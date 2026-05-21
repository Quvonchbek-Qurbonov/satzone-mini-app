from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import DbSession
from app.models.enums import UserRole
from app.models.user import MiniAppUser

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: DbSession,
) -> MiniAppUser:
    if creds is None or not creds.credentials:
        raise UnauthorizedError("Missing access token", code="missing_token")
    payload = decode_access_token(creds.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload", code="invalid_token")
    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise UnauthorizedError("Invalid token payload", code="invalid_token") from exc
    user = await session.get(MiniAppUser, uid)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found", code="invalid_user")
    return user


async def get_current_admin(
    user: Annotated[MiniAppUser, Depends(get_current_user)],
) -> MiniAppUser:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin role required", code="admin_required")
    return user


CurrentUser = Annotated[MiniAppUser, Depends(get_current_user)]
CurrentAdmin = Annotated[MiniAppUser, Depends(get_current_admin)]
