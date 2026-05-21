from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import UserRole
from app.schemas.base import ORMModel

_PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")


def normalize_phone(value: str) -> str:
    cleaned = re.sub(r"[\s\-().]", "", value or "")
    if not _PHONE_RE.match(cleaned):
        raise ValueError(
            "phone_number must be E.164-ish: 8-15 digits, optional leading '+'"
        )
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=10, max_length=4096)


class TelegramContactRequest(BaseModel):
    init_data: str = Field(min_length=10, max_length=4096)
    phone_number: str = Field(min_length=4, max_length=32)
    contact_user_id: int

    @field_validator("phone_number")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        return normalize_phone(v)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthStartResponse(BaseModel):
    """Returned from /auth/telegram. Either tokens or a 'needs_contact' state."""

    status: Literal["authenticated", "needs_contact"]
    tokens: TokenResponse | None = None
    telegram_user: dict | None = None


class MeRead(ORMModel):
    id: uuid.UUID
    telegram_user_id: int
    phone_number: str
    full_name: str
    username: str | None = None
    role: UserRole
    satzone_user_id: uuid.UUID | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
