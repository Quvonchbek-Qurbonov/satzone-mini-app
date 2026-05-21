from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    ForbiddenError,
    UnauthorizedError,
)
from app.core.logging import get_logger
from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
    issue_access_token,
    refresh_expiry,
)
from app.models.enums import UserRole
from app.models.user import MiniAppSession, MiniAppUser
from app.schemas.auth import AuthStartResponse, TokenResponse
from app.services import satzone_client
from app.services.telegram_service import TelegramInitData

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _client_meta(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ua = request.headers.get("User-Agent", "")[:255] or None
    xff = request.headers.get("X-Forwarded-For")
    ip = xff.split(",")[0].strip() if xff else (
        request.client.host if request.client else None
    )
    return ua, ip


async def _mint_tokens(
    session: AsyncSession,
    user: MiniAppUser,
    request: Request | None,
) -> TokenResponse:
    access, ttl = issue_access_token(
        user_id=str(user.id), role=user.role.value, tg_id=user.telegram_user_id
    )
    refresh = generate_refresh_token()
    rh = hash_refresh_token(refresh)
    ua, ip = _client_meta(request)
    session.add(
        MiniAppSession(
            user_id=user.id,
            refresh_hash=rh,
            user_agent=ua,
            ip_address=ip,
            created_at=_now(),
            expires_at=refresh_expiry(),
        )
    )
    user.last_login_at = _now()
    await session.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ttl,
    )


async def authenticate_existing(
    session: AsyncSession,
    init: TelegramInitData,
    request: Request | None,
) -> AuthStartResponse:
    """If the Telegram user is already linked, mint fresh tokens.

    Otherwise return a ``needs_contact`` signal; the frontend will ask the
    user to share their phone via Telegram's contact-share prompt.
    """
    stmt = select(MiniAppUser).where(
        MiniAppUser.telegram_user_id == init.user.id
    )
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        return AuthStartResponse(
            status="needs_contact",
            telegram_user={
                "id": init.user.id,
                "first_name": init.user.first_name,
                "last_name": init.user.last_name,
                "username": init.user.username,
            },
        )
    if not user.is_active:
        raise ForbiddenError("Account disabled", code="account_disabled")
    tokens = await _mint_tokens(session, user, request)
    return AuthStartResponse(status="authenticated", tokens=tokens)


async def link_contact_and_authenticate(
    session: AsyncSession,
    init: TelegramInitData,
    phone_number: str,
    contact_user_id: int,
    request: Request | None,
) -> TokenResponse:
    """Verify the shared contact's owner, look up the satzone account, link, mint tokens.

    Telegram guarantees the contact card the user *shares* is theirs: the
    ``contact.user_id`` from ``requestContact`` matches the initiator's user
    ID. We re-verify that match here to stop a user pasting somebody else's
    contact card.
    """
    if contact_user_id != init.user.id:
        raise ForbiddenError(
            "Shared contact does not belong to the current user",
            code="contact_user_mismatch",
        )

    role = UserRole.STUDENT
    satzone_user_id = None
    full_name = init.user.full_name

    if phone_number in settings.admin_phone_set:
        role = UserRole.ADMIN
    else:
        satzone_user = await satzone_client.find_user_by_phone(phone_number)
        if satzone_user is None:
            raise UnauthorizedError(
                "This phone is not registered on the website yet",
                code="not_registered",
            )
        if not satzone_user.is_active:
            raise ForbiddenError(
                "Account is disabled on the main platform",
                code="account_disabled",
            )
        if not satzone_user.is_phone_verified:
            raise ForbiddenError(
                "Verify your phone on the main website first",
                code="phone_not_verified_on_website",
            )
        satzone_user_id = satzone_user.id
        if satzone_user.full_name:
            full_name = satzone_user.full_name

    # Upsert by telegram_user_id, then by phone if a row already exists for
    # the phone (e.g. user switched Telegram accounts but same phone).
    user = (
        await session.execute(
            select(MiniAppUser).where(
                MiniAppUser.telegram_user_id == init.user.id
            )
        )
    ).scalar_one_or_none()
    if user is None:
        user = (
            await session.execute(
                select(MiniAppUser).where(MiniAppUser.phone_number == phone_number)
            )
        ).scalar_one_or_none()

    if user is None:
        user = MiniAppUser(
            telegram_user_id=init.user.id,
            phone_number=phone_number,
            full_name=full_name,
            username=init.user.username,
            role=role,
            satzone_user_id=satzone_user_id,
            is_active=True,
        )
        session.add(user)
    else:
        user.telegram_user_id = init.user.id
        user.phone_number = phone_number
        user.full_name = full_name or user.full_name
        user.username = init.user.username or user.username
        user.role = role
        user.satzone_user_id = satzone_user_id
        user.is_active = True

    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "Could not link account — please try again",
            code="link_failed",
            status_code=409,
        ) from exc

    return await _mint_tokens(session, user, request)


async def refresh_tokens(
    session: AsyncSession,
    raw_refresh: str,
    request: Request | None,
) -> TokenResponse:
    rh = hash_refresh_token(raw_refresh)
    row = (
        await session.execute(
            select(MiniAppSession).where(MiniAppSession.refresh_hash == rh)
        )
    ).scalar_one_or_none()
    if row is None:
        raise UnauthorizedError(
            "Invalid refresh token", code="invalid_refresh_token"
        )
    if row.revoked_at is not None:
        # Reuse: revoke all sessions for this user.
        logger.warning("refresh_token_reuse", user_id=str(row.user_id))
        await session.execute(
            update(MiniAppSession)
            .where(
                MiniAppSession.user_id == row.user_id,
                MiniAppSession.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
        await session.commit()
        raise UnauthorizedError(
            "Refresh token reuse detected", code="token_reuse"
        )
    if row.expires_at <= _now():
        raise UnauthorizedError("Refresh token expired", code="refresh_expired")

    user = await session.get(MiniAppUser, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or disabled", code="invalid_user")

    # Rotate.
    row.revoked_at = _now()
    new_refresh = generate_refresh_token()
    session.add(
        MiniAppSession(
            user_id=user.id,
            refresh_hash=hash_refresh_token(new_refresh),
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            created_at=_now(),
            expires_at=refresh_expiry(),
        )
    )
    access, ttl = issue_access_token(
        user_id=str(user.id), role=user.role.value, tg_id=user.telegram_user_id
    )
    await session.commit()
    return TokenResponse(
        access_token=access, refresh_token=new_refresh, expires_in=ttl
    )


async def logout(session: AsyncSession, raw_refresh: str) -> None:
    rh = hash_refresh_token(raw_refresh)
    await session.execute(
        update(MiniAppSession)
        .where(MiniAppSession.refresh_hash == rh, MiniAppSession.revoked_at.is_(None))
        .values(revoked_at=_now())
    )
    await session.commit()
