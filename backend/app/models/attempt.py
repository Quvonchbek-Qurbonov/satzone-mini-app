from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import AttemptStatus

attempt_status_enum = PgEnum(
    AttemptStatus,
    name="miniapp_attempt_status",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class MockAttempt(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mock_attempts"
    __table_args__ = (
        CheckConstraint(
            "score_percent BETWEEN 0 AND 100", name="attempt_score_pct_range"
        ),
        Index(
            "ix_attempts_user_submitted",
            "user_id",
            "submitted_at",
        ),
        # At most one in-progress attempt per (mock, user) at a time.
        Index(
            "uq_attempt_open",
            "mock_id",
            "user_id",
            unique=True,
            postgresql_where=(
                "submitted_at IS NULL"
            ),
        ),
    )

    mock_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("miniapp_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AttemptStatus] = mapped_column(
        attempt_status_enum,
        nullable=False,
        default=AttemptStatus.IN_PROGRESS,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_module_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mock_modules.id", ondelete="SET NULL")
    )

    answers: Mapped[list["MockAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class MockAnswer(UUIDPKMixin, Base):
    __tablename__ = "mock_answers"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "question_id", name="uq_answer_attempt_question"
        ),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response: Mapped[dict | list | None] = mapped_column(JSONB)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    awarded_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    attempt: Mapped[MockAttempt] = relationship(back_populates="answers")
