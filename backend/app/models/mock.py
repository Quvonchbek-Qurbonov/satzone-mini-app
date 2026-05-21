from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import MockKind, MockStatus, QuestionType

mock_kind_enum = PgEnum(
    MockKind,
    name="miniapp_mock_kind",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)
mock_status_enum = PgEnum(
    MockStatus,
    name="miniapp_mock_status",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)
question_type_enum = PgEnum(
    QuestionType,
    name="miniapp_question_type",
    create_type=False,
    values_callable=lambda x: [e.value for e in x],
)


class Mock(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mocks"
    __table_args__ = (
        CheckConstraint("pass_percent BETWEEN 0 AND 100", name="mock_pass_pct_range"),
        CheckConstraint("total_minutes > 0", name="mock_total_minutes_positive"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[MockKind] = mapped_column(
        mock_kind_enum, nullable=False, default=MockKind.SAT_RW
    )
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    pass_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[MockStatus] = mapped_column(
        mock_status_enum, nullable=False, default=MockStatus.DRAFT, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("miniapp_users.id", ondelete="SET NULL")
    )

    modules: Mapped[list["MockModule"]] = relationship(
        back_populates="mock",
        cascade="all, delete-orphan",
        order_by="MockModule.order",
    )


class MockModule(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mock_modules"
    __table_args__ = (
        UniqueConstraint("mock_id", "order", name="uq_module_mock_order"),
        CheckConstraint("time_limit_minutes > 0", name="module_time_positive"),
    )

    mock_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=32)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    mock: Mapped[Mock] = relationship(back_populates="modules")
    passages: Mapped[list["MockPassage"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="MockPassage.order",
    )
    questions: Mapped[list["MockQuestion"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="MockQuestion.order",
    )


class MockPassage(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mock_passages"
    __table_args__ = (
        UniqueConstraint("module_id", "order", name="uq_passage_module_order"),
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200))
    subtitle: Mapped[str | None] = mapped_column(String(255))
    body_html: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    module: Mapped[MockModule] = relationship(back_populates="passages")


class MockQuestion(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mock_questions"
    __table_args__ = (
        UniqueConstraint("module_id", "order", name="uq_question_module_order"),
        CheckConstraint("points >= 0", name="question_points_non_negative"),
    )

    module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mock_passages.id", ondelete="SET NULL"),
        index=True,
    )
    type: Mapped[QuestionType] = mapped_column(question_type_enum, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expected_answers: Mapped[list[str] | None] = mapped_column(JSONB)

    module: Mapped[MockModule] = relationship(back_populates="questions")
    options: Mapped[list["MockOption"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="MockOption.order",
    )


class MockOption(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "mock_options"
    __table_args__ = (
        UniqueConstraint("question_id", "order", name="uq_option_question_order"),
    )

    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mock_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500))

    question: Mapped[MockQuestion] = relationship(back_populates="options")
