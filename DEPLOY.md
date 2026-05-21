# Deploying to production — satzonemini.me

Target: a fresh Ubuntu 22.04 / 24.04 LTS VPS. The satzone backend already
runs on a **different** server in the same provider/region. We'll connect
the two privately via Tailscale (free for personal use, no DB ports exposed
to the internet).

Walk through the steps in order. Each step is independent and idempotent;
you can rerun a step safely if you make a mistake.

---

## Step 1 — DNS

On the **mini-app server**, get its public IPv4:

```bash
curl -4 ifconfig.me
```

At your domain registrar for `satzonemini.me`:

| Type | Name | Value | TTL |
| ---- | ---- | ----- | --- |
| A    | `@`  | `<the IPv4 you just printed>` | 300 |
| A    | `www` | `<the same IPv4>` | 300 |

(If your registrar doesn't accept `@`, leave the host field blank.)

After ~5–30 minutes, verify from anywhere:

```bash
dig +short satzonemini.me
# should print your server IP
```

> Until DNS resolves, **do not** start the production stack — Caddy will
> burn one of its Let's Encrypt rate-limit slots on a failed cert request.

---

## Step 2 — Server hardening

SSH in:

```bash
ssh root@satzonemini.me   # use IP if DNS not propagated yet
```

Create a non-root user:

```bash
adduser deploy
usermod -aG sudo deploy
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

Disable root SSH and password auth (optional but strongly recommended).
Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication no
```

Reload SSH (keeps your current session alive):

```bash
systemctl reload ssh   # or `sshd` on some images
```

Reconnect as the deploy user from a **new** terminal:

```bash
ssh deploy@satzonemini.me
```

Install Docker + plugin (official script, idempotent):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and back in so the group takes effect, then verify:

```bash
docker --version
docker compose version
```

Firewall (UFW):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp     # HTTP/3
sudo ufw enable
sudo ufw status
```

---

## Step 3 — Private connection to the satzone DB (Tailscale)

The mini-app BFF needs read access to satzone's `users` and `enrollments`
tables. **Do not** expose satzone's Postgres on the public internet — put
both servers on a Tailscale tailnet and listen on the Tailscale interface
only.

### 3a. On **both** servers, install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sudo sh
sudo tailscale up
```

The command prints a one-time URL; open it in your browser, sign in (Google
account is fine for the free plan), approve both machines.

### 3b. Get the satzone server's tailscale IP

SSH to your **satzone server**, then:

```bash
tailscale ip -4
# prints e.g. 100.64.10.42
```

Note that IP — you'll use it later as `SATZONE_DB_HOST`.

### 3c. Make satzone's Postgres listen on the tailscale interface

Still on the satzone server. Find the active Postgres config:

```bash
sudo -u postgres psql -c "SHOW config_file;"
# e.g. /etc/postgresql/16/main/postgresql.conf
```

Edit `postgresql.conf`:

```
listen_addresses = 'localhost,100.64.10.42'   # add your tailscale IP
```

Edit `pg_hba.conf` (same directory) — add one line allowing the mini-app
server's tailscale IP (find it with `tailscale ip -4` on the **mini-app**
server, then come back here):

```
host    satzone    miniapp_ro    100.64.10.99/32    scram-sha-256
```

Restart Postgres:

```bash
sudo systemctl restart postgresql
```

### 3d. Create the read-only role on satzone's DB

Copy the SQL file to the satzone server, edit the password placeholder, run it:

```bash
# On your laptop:
scp D:/Project/mini-app/backend/ops/satzone-ro.sql deploy@<satzone-ip>:/tmp/

# On the satzone server:
nano /tmp/satzone-ro.sql                              # set a strong password
sudo -u postgres psql -d satzone -f /tmp/satzone-ro.sql
rm /tmp/satzone-ro.sql
```

### 3e. Smoke-test from the mini-app server

```bash
sudo apt install -y postgresql-client
PGPASSWORD='<the password you set>' psql \
  -h 100.64.10.42 -p 5432 -U miniapp_ro -d satzone \
  -c "SELECT count(*) FROM users;"
```

If you see a number, networking is good. If you see "connection refused" or
"no pg_hba.conf entry," recheck Step 3c.

---

## Step 4 — Push the mini-app code to the server

On your **laptop**, push the repo to GitHub (private repo is fine):

```powershell
cd D:\Project\mini-app
git init
git add .
git commit -m "Initial commit"
git remote add origin git@github.com:<you>/sat-miniapp.git
git push -u origin main
```

On the **mini-app server**:

```bash
cd /home/deploy
git clone git@github.com:<you>/sat-miniapp.git mini-app   # or HTTPS
cd mini-app
cp .env.production.example .env
nano .env
```

Fill in `.env`:

| Key | How to set it |
| --- | --- |
| `POSTGRES_PASSWORD` | `openssl rand -base64 24` |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `ADMIN_PHONES` | Your phone in E.164 (`+998...`) |
| `SATZONE_DB_HOST` | The satzone server's tailscale IP (from Step 3b) |
| `SATZONE_DB_PASSWORD` | The password you set in Step 3d |
| `WEBSITE_URL` | The satzone main-site URL |

Leave `SATZONE_API_BASE` and `SATZONE_ADMIN_TOKEN` blank — the BFF uses
read-only SQL for everything.

---

## Step 5 — First boot

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This takes ~3 minutes the first time (Docker pulls base images, builds
both app images, applies migrations, Caddy fetches a Let's Encrypt cert).

Watch logs in another shell:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Wait until you see:

- `api-1 | INFO: Uvicorn running on http://0.0.0.0:8000`
- `caddy-1 | certificate obtained successfully` (one per domain)

Then verify from your laptop:

```powershell
curl https://satzonemini.me/api/v1/health
# {"status":"ok"}
curl https://satzonemini.me/api/v1/ready
# {"status":"ready","db":true,"redis":true}
```

Open `https://satzonemini.me` in a browser — it should show the "Open in
Telegram" splash (correct: the SPA can only run inside Telegram in production).

---

## Step 6 — Configure BotFather

In Telegram, open **@BotFather**:

1. `/mybots` → pick your bot → **Bot Settings**
2. **Menu Button** → **Configure Menu Button** → URL `https://satzonemini.me`,
   button text `Mocks`
3. (Optional) **Bot Settings** → **Configure Mini App** → URL `https://satzonemini.me`

Open your bot in Telegram, tap the **Menu** button at the bottom-left of
the chat. The app loads.

First time as an admin: tap "Share my phone" → admin allowlist matches →
you land in `/admin`. Create your first mock for a course.

Re-test as a student (a phone that's registered on the main website but
NOT in `ADMIN_PHONES`): same share flow → you land in `/home` → see the
course → take the mock.

---

## Operations

### Updates

```bash
cd /home/deploy/mini-app
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Zero downtime is not the goal here — the rolling restart takes ~10 seconds.

### Logs

```bash
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs --tail 200 caddy
```

### Database backups

Cron the following on the mini-app server (e.g. `crontab -e`):

```cron
0 3 * * * cd /home/deploy/mini-app && docker compose -f docker-compose.prod.yml exec -T miniapp-db pg_dump -U miniapp miniapp | gzip > /home/deploy/backups/miniapp-$(date +\%F).sql.gz
0 4 * * * find /home/deploy/backups -name "miniapp-*.sql.gz" -mtime +14 -delete
```

Restore:

```bash
gunzip -c /home/deploy/backups/miniapp-2026-05-21.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T miniapp-db psql -U miniapp miniapp
```

### Shell into a container

```bash
docker compose -f docker-compose.prod.yml exec api sh
```

### Reset everything (DANGER — wipes the DB)

```bash
docker compose -f docker-compose.prod.yml down -v
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| `dig +short satzonemini.me` returns nothing | DNS not propagated yet | Wait or check at your registrar |
| Caddy logs `tls: unable to get certificate` | Port 80 unreachable from the public internet, or DNS wrong | Check UFW + DNS |
| `satzone_unavailable` in api logs | Tailscale not connected, or pg_hba.conf wrong | Test with `psql` from the mini-app server (Step 3e) |
| `invalid_init_data` after sharing contact | `TELEGRAM_BOT_TOKEN` wrong | Double-check the token in `.env` and restart api |
| `not_registered` for a phone that IS on the website | `is_phone_verified=false` on satzone | Verify the phone on the main website first |
| 502 from Caddy | The frontend container crashed | `docker compose -f docker-compose.prod.yml logs frontend` |
| API returns 429 a lot | Rate limit too strict for your usage | Raise `RATE_LIMIT_DEFAULT_PER_MIN` in `.env`, restart api |
