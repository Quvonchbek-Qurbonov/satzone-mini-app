"""Smoke tests for the Telegram initData HMAC verifier.

We construct a payload, sign it with a known bot token, then verify it
round-trips through ``validate_init_data``. Then we tamper with the hash
and confirm the verifier rejects it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "1234567890:test-bot-token")
os.environ.setdefault("POSTGRES_PASSWORD", "x")
os.environ.setdefault("SATZONE_DB_PASSWORD", "x")


def _sign(payload: dict, bot_token: str) -> str:
    data_check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload.keys()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()


def _build_init_data(*, bot_token: str, user: dict, auth_date: int | None = None) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "user": json.dumps(user),
        "query_id": "AAAA",
    }
    payload["hash"] = _sign(payload, bot_token)
    return urlencode(payload)


def test_valid_signature_round_trips():
    from app.services.telegram_service import validate_init_data
    from app.core.config import settings

    init = _build_init_data(
        bot_token=settings.TELEGRAM_BOT_TOKEN,
        user={"id": 42, "first_name": "Test", "username": "tu"},
    )
    parsed = validate_init_data(init)
    assert parsed.user.id == 42
    assert parsed.user.first_name == "Test"
    assert parsed.user.username == "tu"


def test_tampered_hash_rejected():
    from app.services.telegram_service import validate_init_data
    from app.core.exceptions import UnauthorizedError
    from app.core.config import settings

    init = _build_init_data(
        bot_token=settings.TELEGRAM_BOT_TOKEN,
        user={"id": 42, "first_name": "Test"},
    )
    # Flip a character in the hash.
    init = init.replace("hash=", "hash=0", 1)
    with pytest.raises(UnauthorizedError):
        validate_init_data(init)


def test_expired_init_data_rejected():
    from app.services.telegram_service import validate_init_data
    from app.core.exceptions import UnauthorizedError
    from app.core.config import settings

    init = _build_init_data(
        bot_token=settings.TELEGRAM_BOT_TOKEN,
        user={"id": 42, "first_name": "Test"},
        auth_date=int(time.time()) - settings.TELEGRAM_INIT_DATA_TTL_SECONDS - 60,
    )
    with pytest.raises(UnauthorizedError):
        validate_init_data(init)
