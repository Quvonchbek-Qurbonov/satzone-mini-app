# SAT Mock — Telegram Mini App

A Telegram Mini App where students enrolled in courses on the **satzone** main
website take SAT mock tests. Admins (identified by phone numbers in `.env`)
author mocks per course.

The mini app does **not** modify the satzone backend (`D:\Project\satzone`).
It connects to satzone's Postgres in read-only mode (`miniapp_ro` role) and
stores everything mock-related in its own Postgres database.

## Stack

- **Frontend** — React 18 + Vite + TypeScript + Tailwind + Zustand + React Query + KaTeX + `@twa-dev/sdk`
- **Backend (BFF)** — FastAPI (Python 3.13), SQLAlchemy 2.0 async, asyncpg, Alembic, Redis, structlog, PyJWT
- **Auth** — Telegram WebApp `initData` HMAC validation + Telegram contact-share → mini-app-owned JWT

## Repository layout

```
mini-app/
├── backend/      FastAPI BFF + Alembic migrations + tests
├── frontend/     Vite SPA (Telegram Mini App)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quickstart (local dev)

### 1) Bring up the satzone backend (separate repo, untouched)

```powershell
cd D:\Project\satzone
docker compose up -d db redis api
docker compose exec api alembic upgrade head
```

### 2) Create the read-only role inside satzone's Postgres

```powershell
docker compose exec db psql -U satzone -d satzone -f -
# paste D:\Project\mini-app\backend\ops\satzone-ro.sql
# (edit the password in that file first)
```

The role lets the mini app `SELECT` from `users`, `courses`, `instructors`,
and `enrollments` — and nothing else.

### 3) Configure & start the mini app

```powershell
cd D:\Project\mini-app
Copy-Item .env.example .env
# Fill in:
#   TELEGRAM_BOT_TOKEN (from @BotFather)
#   JWT_SECRET         (python -c "import secrets; print(secrets.token_hex(32))")
#   SATZONE_DB_PASSWORD (the password you set in satzone-ro.sql)
#   ADMIN_PHONES        (your phone in E.164, e.g. +998901234567)
docker compose up -d --build
```

The backend's Alembic migrations run automatically on container start. After
about ten seconds:

- API: <http://localhost:8000/api/v1/openapi.json>
- Swagger UI: <http://localhost:8000/docs>
- Frontend: <http://localhost:5173>

### 4) Expose the frontend to Telegram for end-to-end testing

Telegram Mini Apps need an HTTPS URL. The simplest local option is a
Cloudflare tunnel:

```powershell
cloudflared tunnel --url http://localhost:5173
```

Copy the `https://...trycloudflare.com` URL the command prints, then in
@BotFather:

1. `/mybots` → select your bot → **Bot Settings** → **Configure Mini App**
2. Paste the HTTPS URL.

Open your bot in Telegram, tap **Open App**.

## End-to-end flow

1. User opens the Mini App.
2. Frontend reads `WebApp.initData` and POSTs it to `/api/v1/auth/telegram`.
3. If the Telegram user is already linked, tokens come back. Otherwise the
   frontend asks the user to share their phone (`WebApp.requestContact`).
4. The shared phone is POSTed to `/api/v1/auth/telegram/contact` together
   with the `initData`. The BFF re-verifies the HMAC, looks up the phone in
   satzone (read-only), creates a `miniapp_users` row, and returns tokens.
5. Students see their enrolled courses → mocks → mock player.
6. Admins (phones in `ADMIN_PHONES`) skip the satzone lookup and land in the
   admin UI at `/admin`, where they can create / edit / publish mocks for
   every course.

## Auth and security

- **initData HMAC** — see `backend/app/services/telegram_service.py`.
  Implements the Telegram spec exactly; the `auth_date` claim is rejected if
  older than `TELEGRAM_INIT_DATA_TTL_SECONDS`.
- **JWT** — HS256, 15 min access TTL. Refresh tokens are 32-byte random,
  hashed with SHA-256 at rest, rotated on every refresh, and **reuse
  detection** revokes every refresh token for the user.
- **Phone trust** — Telegram only allows users to share *their own* contact
  card; the BFF re-verifies `contact.user_id === initData.user.id` to stop a
  malicious frontend pasting somebody else's contact.
- **Read-only satzone access** — the `miniapp_ro` Postgres role only has
  `SELECT` on three tables. Mutations raise at the Postgres layer.
- **Strict CSP** — the SPA's nginx config restricts script / connect / frame
  origins. `frame-ancestors` allows only Telegram domains.

## Tests

```powershell
cd backend
pip install -r requirements.txt
pytest -q
```

Covers initData HMAC (good signature, tampered, expired) and per-question
grading (single choice, multi choice, grid-in normalization).

## Production hardening checklist

- [ ] Set `ENV=production`, `DEBUG=false`, `LOG_JSON=true`.
- [ ] Set strong `JWT_SECRET` (32 bytes hex) and `POSTGRES_PASSWORD`.
- [ ] Run `ops/satzone-ro.sql` with a **strong** password — do not commit it.
- [ ] Put the API behind a reverse proxy that terminates TLS and sets
      `X-Forwarded-For`.
- [ ] Restrict `BACKEND_CORS_ORIGINS` to the deployed frontend host.
- [ ] Use a managed Postgres + Redis with backups.
- [ ] Switch `STORAGE_BACKEND` to `s3` (or wire CloudFront in front) and set
      `AWS_*` + `AWS_S3_PUBLIC_BASE_URL`.
- [ ] Configure `frame-ancestors` in `frontend/nginx.conf` to lock the SPA
      to Telegram domains only.
- [ ] Configure your CI to run `pytest` and `tsc -b --noEmit` on every PR.

## Things that will trip you up

- **Telegram and HTTPS** — Telegram clients refuse to load Mini Apps over
  plain HTTP. Use Cloudflared / ngrok during development.
- **initData expiry** — the signature is bound to `auth_date`. If the user
  leaves the app open for >24h, `/auth/telegram` will return
  `init_data_expired`. The frontend re-reads `WebApp.initData` and retries
  on `Splash`.
- **Satzone DB host inside Docker** — when both stacks run on the same
  machine, set `SATZONE_DB_HOST=host.docker.internal` (the
  `docker-compose.yml` already adds the matching `extra_hosts` entry).
- **One in-progress attempt** — the schema enforces a unique partial index
  on `(mock_id, user_id) WHERE submitted_at IS NULL`. Calling
  `POST /mocks/{id}/attempts` while another is open returns the existing
  attempt instead of erroring.
- **Server-side timer is authoritative** — clients can't trick the timer by
  changing their clock; `submit_attempt` clamps `time_spent_seconds` and
  uses the stored `deadline_at` for the `expired` status.
