"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-05-21
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init"
down_revision: str | Sequence[str] | None = None
branch_labels = None
depends_on = None


# Define each Postgres ENUM once and reuse it across every column definition.
# ``create_type=False`` keeps Alembic from emitting an extra empty ``CREATE TYPE``
# inside the ``CREATE TABLE``; we create them explicitly below before the tables.
role_enum = postgresql.ENUM(
    "student", "admin", name="miniapp_user_role", create_type=False
)
mock_kind_enum = postgresql.ENUM(
    "sat_rw", "sat_math", "generic", name="miniapp_mock_kind", create_type=False
)
mock_status_enum = postgresql.ENUM(
    "draft", "published", "archived", name="miniapp_mock_status", create_type=False
)
question_type_enum = postgresql.ENUM(
    "single_choice",
    "multi_choice",
    "grid_in",
    "short_answer",
    name="miniapp_question_type",
    create_type=False,
)
attempt_status_enum = postgresql.ENUM(
    "in_progress",
    "submitted",
    "expired",
    name="miniapp_attempt_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    role_enum.create(bind, checkfirst=True)
    mock_kind_enum.create(bind, checkfirst=True)
    mock_status_enum.create(bind, checkfirst=True)
    question_type_enum.create(bind, checkfirst=True)
    attempt_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "miniapp_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("username", sa.String(length=64)),
        sa.Column("role", role_enum, nullable=False, server_default="student"),
        sa.Column("satzone_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_miniapp_users_telegram_user_id",
        "miniapp_users",
        ["telegram_user_id"],
    )
    op.create_index(
        "ix_miniapp_users_phone_number", "miniapp_users", ["phone_number"]
    )

    op.create_table(
        "miniapp_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("miniapp_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(length=255)),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_miniapp_sessions_user_id", "miniapp_sessions", ["user_id"])

    op.create_table(
        "mocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("instructions", sa.Text()),
        sa.Column("kind", mock_kind_enum, nullable=False, server_default="sat_rw"),
        sa.Column("total_minutes", sa.Integer(), nullable=False, server_default="64"),
        sa.Column("pass_percent", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("status", mock_status_enum, nullable=False, server_default="draft"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("miniapp_users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("pass_percent BETWEEN 0 AND 100", name="mock_pass_pct_range"),
        sa.CheckConstraint("total_minutes > 0", name="mock_total_minutes_positive"),
    )
    op.create_index("ix_mocks_course_id", "mocks", ["course_id"])
    op.create_index("ix_mocks_status", "mocks", ["status"])

    op.create_table(
        "mock_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "mock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "time_limit_minutes", sa.Integer(), nullable=False, server_default="32"
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("mock_id", "order", name="uq_module_mock_order"),
        sa.CheckConstraint("time_limit_minutes > 0", name="module_time_positive"),
    )
    op.create_index("ix_mock_modules_mock_id", "mock_modules", ["mock_id"])

    op.create_table(
        "mock_passages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "module_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_modules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200)),
        sa.Column("subtitle", sa.String(length=255)),
        sa.Column("body_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("module_id", "order", name="uq_passage_module_order"),
    )
    op.create_index("ix_mock_passages_module_id", "mock_passages", ["module_id"])

    op.create_table(
        "mock_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "module_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_modules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "passage_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_passages.id", ondelete="SET NULL"),
        ),
        sa.Column("type", question_type_enum, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text()),
        sa.Column("image_url", sa.String(length=500)),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_answers", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("module_id", "order", name="uq_question_module_order"),
        sa.CheckConstraint("points >= 0", name="question_points_non_negative"),
    )
    op.create_index("ix_mock_questions_module_id", "mock_questions", ["module_id"])
    op.create_index("ix_mock_questions_passage_id", "mock_questions", ["passage_id"])

    op.create_table(
        "mock_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "is_correct", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("image_url", sa.String(length=500)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("question_id", "order", name="uq_option_question_order"),
    )
    op.create_index("ix_mock_options_question_id", "mock_options", ["question_id"])

    op.create_table(
        "mock_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "mock_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mocks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("miniapp_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", attempt_status_enum, nullable=False, server_default="in_progress"
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "time_spent_seconds", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("score_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "current_module_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_modules.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "score_percent BETWEEN 0 AND 100", name="attempt_score_pct_range"
        ),
    )
    op.create_index("ix_mock_attempts_mock_id", "mock_attempts", ["mock_id"])
    op.create_index("ix_mock_attempts_user_id", "mock_attempts", ["user_id"])
    op.create_index("ix_mock_attempts_status", "mock_attempts", ["status"])
    op.create_index(
        "ix_attempts_user_submitted",
        "mock_attempts",
        ["user_id", "submitted_at"],
    )
    op.create_index(
        "uq_attempt_open",
        "mock_attempts",
        ["mock_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("submitted_at IS NULL"),
    )

    op.create_table(
        "mock_answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mock_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("response", postgresql.JSONB()),
        sa.Column(
            "is_correct", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "awarded_points", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "attempt_id", "question_id", name="uq_answer_attempt_question"
        ),
    )
    op.create_index("ix_mock_answers_attempt_id", "mock_answers", ["attempt_id"])
    op.create_index("ix_mock_answers_question_id", "mock_answers", ["question_id"])


def downgrade() -> None:
    op.drop_table("mock_answers")
    op.drop_table("mock_attempts")
    op.drop_table("mock_options")
    op.drop_table("mock_questions")
    op.drop_table("mock_passages")
    op.drop_table("mock_modules")
    op.drop_table("mocks")
    op.drop_table("miniapp_sessions")
    op.drop_table("miniapp_users")
    for enum_name in (
        "miniapp_attempt_status",
        "miniapp_question_type",
        "miniapp_mock_status",
        "miniapp_mock_kind",
        "miniapp_user_role",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
