from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import AttemptStatus, MockKind
from app.schemas.base import ORMModel
from app.schemas.mock import ModuleStudentRead


class AnswerWrite(ORMModel):
    question_id: uuid.UUID
    selected_option_ids: list[uuid.UUID] | None = None
    text: str | None = None
    flagged: bool = False


class AnswerRead(ORMModel):
    question_id: uuid.UUID
    response: dict | list | None = None
    is_correct: bool = False
    awarded_points: int = 0
    flagged: bool = False


class AttemptStart(ORMModel):
    id: uuid.UUID
    mock_id: uuid.UUID
    started_at: datetime
    deadline_at: datetime
    status: AttemptStatus


class AttemptRead(ORMModel):
    id: uuid.UUID
    mock_id: uuid.UUID
    mock_title: str
    mock_kind: MockKind
    pass_percent: int
    status: AttemptStatus
    started_at: datetime
    deadline_at: datetime
    submitted_at: datetime | None = None
    time_spent_seconds: int = 0
    seconds_remaining: int = 0
    score_percent: int = 0
    raw_score: int = 0
    total_points: int = 0
    passed: bool = False
    modules: list[ModuleStudentRead] = Field(default_factory=list)
    answers: list[AnswerRead] = Field(default_factory=list)


class AttemptSubmitResult(ORMModel):
    id: uuid.UUID
    mock_id: uuid.UUID
    submitted_at: datetime
    time_spent_seconds: int
    score_percent: int
    raw_score: int
    total_points: int
    passed: bool


class AttemptHistoryItem(ORMModel):
    id: uuid.UUID
    mock_id: uuid.UUID
    mock_title: str
    mock_kind: MockKind
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None = None
    score_percent: int
    passed: bool
