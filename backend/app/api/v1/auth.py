from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.deps import CurrentUser
from app.db.session import DbSession
from app.middleware.rate_limit import rate_limit_auth
from app.schemas.auth import (
    AuthStartResponse,
    LogoutRequest,
    MeRead,
    RefreshRequest,
    TelegramAuthRequest,
    TelegramContactRequest,
    TokenResponse,
)
from app.schemas.base import Message
from app.services import auth_service
from app.services.telegram_service import validate_init_data

router = APIRouter(
    prefix="/auth", tags=["auth"], dependencies=[Depends(rate_limit_auth)]
)


@router.post("/telegram", response_model=AuthStartResponse)
async def telegram_auth(
    payload: TelegramAuthRequest, request: Request, session: DbSession
) -> AuthStartResponse:
    init = validate_init_data(payload.init_data)
    return await auth_service.authenticate_existing(session, init, request)


@router.post("/telegram/contact", response_model=TokenResponse)
async def telegram_link_contact(
    payload: TelegramContactRequest, request: Request, session: DbSession
) -> TokenResponse:
    init = validate_init_data(payload.init_data)
    return await auth_service.link_contact_and_authenticate(
        session=session,
        init=init,
        phone_number=payload.phone_number,
        contact_user_id=payload.contact_user_id,
        request=request,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, request: Request, session: DbSession
) -> TokenResponse:
    return await auth_service.refresh_tokens(
        session, payload.refresh_token, request
    )


@router.post("/logout", response_model=Message)
async def logout(payload: LogoutRequest, session: DbSession) -> Message:
    await auth_service.logout(session, payload.refresh_token)
    return Message(message="Logged out")


@router.get("/me", response_model=MeRead)
async def me(user: CurrentUser) -> MeRead:
    return MeRead.model_validate(user)
