"""Attempt lifecycle + grading.

The server is the source of truth for time. The client sees a countdown but
mutations are rejected once the server-side deadline passes. Final scoring
runs inside :func:`submit_attempt` so the same code path handles user-initiated
submits and timer-driven auto-submits.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from app.models.attempt import MockAnswer, MockAttempt
from app.models.enums import (
    AttemptStatus,
    MockStatus,
    QuestionType,
    UserRole,
)
from app.models.mock import Mock, MockModule, MockOption, MockQuestion
from app.models.user import MiniAppUser
from app.schemas.attempt import AnswerWrite
from app.services import mock_service, satzone_client


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _grade_question(
    q: MockQuestion, response: dict | list | None
) -> tuple[bool, int]:
    """Return (is_correct, awarded_points) for a stored response."""
    if response is None:
        return False, 0
    points = max(0, int(q.points))

    if q.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE):
        selected_ids = set()
        if isinstance(response, dict):
            ids = response.get("selected_option_ids") or []
        elif isinstance(response, list):
            ids = response
        else:
            ids = []
        for raw in ids:
            try:
                selected_ids.add(uuid.UUID(str(raw)))
            except (ValueError, TypeError):
                continue
        correct_ids = {o.id for o in q.options if o.is_correct}
        if not correct_ids:
            return False, 0
        if q.type == QuestionType.SINGLE_CHOICE:
            ok = selected_ids == correct_ids and len(selected_ids) == 1
        else:
            ok = selected_ids == correct_ids
        return ok, points if ok else 0

    if q.type in (QuestionType.GRID_IN, QuestionType.SHORT_ANSWER):
        text_response: str | None = None
        if isinstance(response, dict):
            text_response = response.get("text")
        elif isinstance(response, str):
            text_response = response
        if not text_response:
            return False, 0
        accepted = {_normalize(a) for a in (q.expected_answers or []) if a}
        ok = _normalize(text_response) in accepted
        return ok, points if ok else 0

    return False, 0


def _serialize_response(payload: AnswerWrite) -> dict[str, Any] | None:
    if payload.selected_option_ids is not None:
        return {
            "selected_option_ids": [
                str(x) for x in payload.selected_option_ids
            ]
        }
    if payload.text is not None:
        return {"text": payload.text}
    return None


def _seconds_remaining(att: MockAttempt) -> int:
    if att.submitted_at is not None:
        return 0
    delta = (att.deadline_at - _now()).total_seconds()
    return max(0, int(delta))


async def _ensure_enrolled_or_admin(
    user: MiniAppUser, mock: Mock
) -> None:
    if user.role == UserRole.ADMIN:
        return
    if user.satzone_user_id is None:
        raise ForbiddenError(
            "Account not linked to a website registration",
            code="not_linked",
        )
    course_ids = await satzone_client.list_user_course_ids(user.satzone_user_id)
    if mock.course_id not in course_ids:
        raise ForbiddenError(
            "You are not enrolled in this mock's course",
            code="not_enrolled",
        )


# ---------- Lifecycle ----------


async def start_attempt(
    session: AsyncSession, user: MiniAppUser, mock_id: uuid.UUID
) -> MockAttempt:
    mock = await mock_service.get_mock_or_404(session, mock_id)
    if mock.status != MockStatus.PUBLISHED and user.role != UserRole.ADMIN:
        raise NotFoundError("Mock not found", code="mock_not_found")
    if not mock.modules:
        raise ValidationAppError(
            "This mock has no modules yet", code="mock_empty"
        )
    await _ensure_enrolled_or_admin(user, mock)

    started = _now()
    deadline = started + timedelta(minutes=mock.total_minutes)
    first_module = mock.modules[0]

    attempt = MockAttempt(
        mock_id=mock.id,
        user_id=user.id,
        status=AttemptStatus.IN_PROGRESS,
        started_at=started,
        deadline_at=deadline,
        current_module_id=first_module.id,
        total_points=sum(
            max(0, int(q.points))
            for module in mock.modules
            for q in module.questions
        ),
    )
    session.add(attempt)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        # uq_attempt_open conflict — return the existing in-progress attempt.
        existing = (
            await session.execute(
                select(MockAttempt).where(
                    MockAttempt.mock_id == mock.id,
                    MockAttempt.user_id == user.id,
                    MockAttempt.submitted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            raise ConflictError(
                "Could not start attempt", code="attempt_start_failed"
            ) from exc
        return existing
    await session.refresh(attempt)
    return attempt


async def _load_attempt_with_answers(
    session: AsyncSession, attempt_id: uuid.UUID
) -> MockAttempt | None:
    stmt = (
        select(MockAttempt)
        .where(MockAttempt.id == attempt_id)
        .options(selectinload(MockAttempt.answers))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_attempt(
    session: AsyncSession,
    user: MiniAppUser,
    attempt_id: uuid.UUID,
) -> tuple[MockAttempt, Mock, int]:
    attempt = await _load_attempt_with_answers(session, attempt_id)
    if attempt is None:
        raise NotFoundError("Attempt not found", code="attempt_not_found")
    if attempt.user_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Not your attempt", code="forbidden")
    mock = await mock_service.get_mock_or_404(session, attempt.mock_id)
    seconds_remaining = _seconds_remaining(attempt)
    return attempt, mock, seconds_remaining


async def upsert_answer(
    session: AsyncSession,
    user: MiniAppUser,
    attempt_id: uuid.UUID,
    payload: AnswerWrite,
) -> MockAnswer:
    attempt = await _load_attempt_with_answers(session, attempt_id)
    if attempt is None:
        raise NotFoundError("Attempt not found", code="attempt_not_found")
    if attempt.user_id != user.id:
        raise ForbiddenError("Not your attempt", code="forbidden")
    if attempt.submitted_at is not None:
        raise ConflictError(
            "Attempt already submitted", code="attempt_already_submitted"
        )
    now = _now()
    if now > attempt.deadline_at + timedelta(seconds=settings.SUBMISSION_GRACE_SECONDS):
        raise ForbiddenError("Time is up", code="attempt_expired")

    q = (
        await session.execute(
            select(MockQuestion)
            .where(MockQuestion.id == payload.question_id)
            .options(selectinload(MockQuestion.options))
        )
    ).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Question not found", code="question_not_found")
    mock_module = await session.get(MockModule, q.module_id)
    if mock_module is None or mock_module.mock_id != attempt.mock_id:
        raise ValidationAppError(
            "Question does not belong to this mock",
            code="question_mock_mismatch",
        )

    existing = next(
        (a for a in attempt.answers if a.question_id == payload.question_id),
        None,
    )
    response = _serialize_response(payload)
    if existing is None:
        existing = MockAnswer(
            attempt_id=attempt.id,
            question_id=payload.question_id,
            response=response,
            flagged=payload.flagged,
            answered_at=now,
        )
        session.add(existing)
    else:
        existing.response = response
        existing.flagged = payload.flagged
        existing.answered_at = now

    await session.commit()
    await session.refresh(existing)
    return existing


async def submit_attempt(
    session: AsyncSession,
    user: MiniAppUser,
    attempt_id: uuid.UUID,
) -> MockAttempt:
    attempt = await _load_attempt_with_answers(session, attempt_id)
    if attempt is None:
        raise NotFoundError("Attempt not found", code="attempt_not_found")
    if attempt.user_id != user.id and user.role != UserRole.ADMIN:
        raise ForbiddenError("Not your attempt", code="forbidden")
    if attempt.submitted_at is not None:
        return attempt  # idempotent

    mock = await mock_service.get_mock_or_404(session, attempt.mock_id)

    # Hydrate questions by id for grading.
    questions_by_id: dict[uuid.UUID, MockQuestion] = {}
    for module in mock.modules:
        for q in module.questions:
            questions_by_id[q.id] = q

    raw_score = 0
    for answer in attempt.answers:
        q = questions_by_id.get(answer.question_id)
        if q is None:
            answer.is_correct = False
            answer.awarded_points = 0
            continue
        ok, pts = _grade_question(q, answer.response)
        answer.is_correct = ok
        answer.awarded_points = pts
        raw_score += pts

    total = sum(max(0, int(q.points)) for q in questions_by_id.values())
    score_pct = int(round((raw_score / total) * 100)) if total > 0 else 0
    now = _now()
    spent = int((now - attempt.started_at).total_seconds())
    spent = min(spent, mock.total_minutes * 60)

    attempt.submitted_at = now
    attempt.status = (
        AttemptStatus.EXPIRED if now > attempt.deadline_at else AttemptStatus.SUBMITTED
    )
    attempt.time_spent_seconds = max(0, spent)
    attempt.score_percent = score_pct
    attempt.raw_score = raw_score
    attempt.total_points = total
    attempt.passed = score_pct >= mock.pass_percent

    await session.commit()
    return attempt


async def list_history(
    session: AsyncSession, user: MiniAppUser
) -> list[MockAttempt]:
    stmt = (
        select(MockAttempt)
        .where(MockAttempt.user_id == user.id)
        .order_by(MockAttempt.started_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())
