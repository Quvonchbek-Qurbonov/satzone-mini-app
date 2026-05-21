from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser
from app.db.session import DbSession
from app.schemas.attempt import (
    AnswerRead,
    AnswerWrite,
    AttemptHistoryItem,
    AttemptRead,
    AttemptStart,
    AttemptSubmitResult,
)
from app.schemas.base import Message
from app.services import attempt_service
from app.api.v1.mocks import _module_read

router = APIRouter(tags=["attempts"])


def _attempt_read(attempt, mock, seconds_remaining: int) -> AttemptRead:
    return AttemptRead(
        id=attempt.id,
        mock_id=attempt.mock_id,
        mock_title=mock.title,
        mock_kind=mock.kind,
        pass_percent=mock.pass_percent,
        status=attempt.status,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        submitted_at=attempt.submitted_at,
        time_spent_seconds=attempt.time_spent_seconds,
        seconds_remaining=seconds_remaining,
        score_percent=attempt.score_percent,
        raw_score=attempt.raw_score,
        total_points=attempt.total_points,
        passed=attempt.passed,
        modules=[_module_read(m) for m in mock.modules],
        answers=[
            AnswerRead(
                question_id=a.question_id,
                response=a.response,
                is_correct=a.is_correct,
                awarded_points=a.awarded_points,
                flagged=a.flagged,
            )
            for a in attempt.answers
        ],
    )


@router.post(
    "/mocks/{mock_id}/attempts",
    response_model=AttemptStart,
    status_code=status.HTTP_201_CREATED,
)
async def start_attempt(
    mock_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> AttemptStart:
    attempt = await attempt_service.start_attempt(session, user, mock_id)
    return AttemptStart(
        id=attempt.id,
        mock_id=attempt.mock_id,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        status=attempt.status,
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptRead)
async def get_attempt(
    attempt_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> AttemptRead:
    attempt, mock, seconds_remaining = await attempt_service.get_attempt(
        session, user, attempt_id
    )
    return _attempt_read(attempt, mock, seconds_remaining)


@router.patch("/attempts/{attempt_id}/answers", response_model=AnswerRead)
async def upsert_answer(
    attempt_id: uuid.UUID,
    payload: AnswerWrite,
    user: CurrentUser,
    session: DbSession,
) -> AnswerRead:
    answer = await attempt_service.upsert_answer(session, user, attempt_id, payload)
    return AnswerRead(
        question_id=answer.question_id,
        response=answer.response,
        is_correct=answer.is_correct,
        awarded_points=answer.awarded_points,
        flagged=answer.flagged,
    )


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptSubmitResult)
async def submit_attempt(
    attempt_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> AttemptSubmitResult:
    attempt = await attempt_service.submit_attempt(session, user, attempt_id)
    return AttemptSubmitResult(
        id=attempt.id,
        mock_id=attempt.mock_id,
        submitted_at=attempt.submitted_at,
        time_spent_seconds=attempt.time_spent_seconds,
        score_percent=attempt.score_percent,
        raw_score=attempt.raw_score,
        total_points=attempt.total_points,
        passed=attempt.passed,
    )


@router.get("/me/attempts", response_model=list[AttemptHistoryItem])
async def list_history(
    user: CurrentUser, session: DbSession
) -> list[AttemptHistoryItem]:
    from sqlalchemy import select
    from app.models.attempt import MockAttempt
    from app.models.mock import Mock

    stmt = (
        select(MockAttempt, Mock)
        .join(Mock, Mock.id == MockAttempt.mock_id)
        .where(MockAttempt.user_id == user.id)
        .order_by(MockAttempt.started_at.desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        AttemptHistoryItem(
            id=attempt.id,
            mock_id=attempt.mock_id,
            mock_title=mock.title,
            mock_kind=mock.kind,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            score_percent=attempt.score_percent,
            passed=attempt.passed,
        )
        for attempt, mock in rows
    ]
