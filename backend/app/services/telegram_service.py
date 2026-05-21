"""Telegram WebApp initData validation.

The Telegram Mini App passes a signed query string (``initData``) to the
frontend. The signature ties the data to the bot token, so a backend that
knows the bot token can verify the payload was issued by Telegram and has
not been tampered with.

Algorithm (per Telegram docs, "Validating data received via the Mini App"):

1. Parse the query string into key/value pairs.
2. Remove the ``hash`` value but keep it for comparison.
3. Sort the remaining keys alphabetically and build a ``\n``-joined
   ``data_check_string`` of ``key=value`` lines.
4. ``secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token.encode())``.
5. Computed signature is ``HMAC_SHA256(key=secret_key, msg=data_check_string).hex()``.
6. Compare to the ``hash`` value in constant time.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ValidationAppError


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
    is_premium: bool

    @property
    def full_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts).strip() or "Telegram User"


@dataclass(frozen=True)
class TelegramInitData:
    user: TelegramUser
    auth_date: int
    query_id: str | None
    chat_type: str | None
    raw: dict[str, str]


def _parse_user(value: str) -> TelegramUser:
    try:
        data: dict[str, Any] = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationAppError("Malformed user blob", code="invalid_init_data") from exc
    if "id" not in data:
        raise ValidationAppError("Missing user.id", code="invalid_init_data")
    return TelegramUser(
        id=int(data["id"]),
        first_name=str(data.get("first_name") or ""),
        last_name=(str(data["last_name"]) if data.get("last_name") else None),
        username=(str(data["username"]) if data.get("username") else None),
        language_code=(
            str(data["language_code"]) if data.get("language_code") else None
        ),
        is_premium=bool(data.get("is_premium", False)),
    )


def validate_init_data(init_data: str) -> TelegramInitData:
    """Verify the signature on a raw Telegram WebApp ``initData`` query string.

    Raises :class:`UnauthorizedError` on signature mismatch or
    :class:`ValidationAppError` on missing/expired pieces.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise UnauthorizedError(
            "Bot token not configured", code="server_misconfigured"
        )

    # ``parse_qsl`` decodes percent-encoded values. Keep blank values so the
    # caller can tell missing from empty.
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    if not pairs:
        raise ValidationAppError("Empty init_data", code="invalid_init_data")

    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise ValidationAppError("Missing hash", code="invalid_init_data")

    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hmac.new(
        b"WebAppData",
        settings.TELEGRAM_BOT_TOKEN.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    computed = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        raise UnauthorizedError("Invalid init_data signature", code="invalid_init_data")

    auth_date_raw = data.get("auth_date")
    if not auth_date_raw or not auth_date_raw.isdigit():
        raise ValidationAppError("Missing auth_date", code="invalid_init_data")
    auth_date = int(auth_date_raw)
    if int(time.time()) - auth_date > settings.TELEGRAM_INIT_DATA_TTL_SECONDS:
        raise UnauthorizedError("init_data expired", code="init_data_expired")

    user_blob = data.get("user")
    if not user_blob:
        raise ValidationAppError(
            "Missing user payload", code="invalid_init_data"
        )
    user = _parse_user(user_blob)

    return TelegramInitData(
        user=user,
        auth_date=auth_date,
        query_id=data.get("query_id"),
        chat_type=data.get("chat_type"),
        raw=data,
    )
