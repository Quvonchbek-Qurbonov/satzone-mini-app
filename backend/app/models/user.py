from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import UserRole

user_role_enum = PgEnum(
    UserRole,
    name="miniapp_user_role",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class MiniAppUser(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "miniapp_users"

    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True, index=True
    )
    phone_number: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    username: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, default=UserRole.STUDENT
    )
    satzone_user_id: Mapped[uuid.UUID | None] = mapped_column(PgUUID(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["MiniAppSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class MiniAppSession(UUIDPKMixin, Base):
    __tablename__ = "miniapp_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("miniapp_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    refresh_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[MiniAppUser] = relationship(back_populates="sessions")
