from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.models.enums import MockKind, MockStatus, QuestionType
from app.schemas.base import ORMModel


# ---------- Options ----------


class OptionWrite(ORMModel):
    text: str = Field(min_length=1)
    is_correct: bool = False
    order: int | None = Field(default=None, ge=0)
    image_url: str | None = None


class OptionStudentRead(ORMModel):
    id: uuid.UUID
    text: str
    order: int = 0
    image_url: str | None = None


class OptionAdminRead(OptionStudentRead):
    is_correct: bool = False


# ---------- Questions ----------


class QuestionWrite(ORMModel):
    type: QuestionType
    prompt: str = Field(min_length=1)
    explanation: str | None = None
    image_url: str | None = None
    points: int = Field(default=1, ge=0)
    order: int | None = Field(default=None, ge=0)
    passage_id: uuid.UUID | None = None
    options: list[OptionWrite] | None = None
    expected_answers: list[str] | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> "QuestionWrite":
        if self.type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE):
            if not self.options or len(self.options) < 2:
                raise ValueError("choice questions need at least 2 options")
            correct = [o for o in self.options if o.is_correct]
            if not correct:
                raise ValueError("at least one option must be marked correct")
            if self.type == QuestionType.SINGLE_CHOICE and len(correct) != 1:
                raise ValueError("single_choice must have exactly one correct option")
        elif self.type in (QuestionType.GRID_IN, QuestionType.SHORT_ANSWER):
            if not self.expected_answers:
                raise ValueError(
                    f"{self.type.value} requires non-empty expected_answers"
                )
        return self


class QuestionUpdate(ORMModel):
    prompt: str | None = Field(default=None, min_length=1)
    explanation: str | None = None
    image_url: str | None = None
    points: int | None = Field(default=None, ge=0)
    order: int | None = Field(default=None, ge=0)
    passage_id: uuid.UUID | None = None
    options: list[OptionWrite] | None = None
    expected_answers: list[str] | None = None


class QuestionStudentRead(ORMModel):
    id: uuid.UUID
    type: QuestionType
    prompt: str
    image_url: str | None = None
    points: int
    order: int
    passage_id: uuid.UUID | None = None
    options: list[OptionStudentRead] = Field(default_factory=list)


class QuestionAdminRead(ORMModel):
    id: uuid.UUID
    type: QuestionType
    prompt: str
    explanation: str | None = None
    image_url: str | None = None
    points: int
    order: int
    passage_id: uuid.UUID | None = None
    expected_answers: list[str] | None = None
    options: list[OptionAdminRead] = Field(default_factory=list)


# ---------- Passages ----------


class PassageWrite(ORMModel):
    title: str | None = None
    subtitle: str | None = None
    body_html: str = ""
    order: int | None = Field(default=None, ge=0)


class PassageRead(ORMModel):
    id: uuid.UUID
    title: str | None = None
    subtitle: str | None = None
    body_html: str
    order: int = 0


# ---------- Modules ----------


class ModuleWrite(ORMModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    time_limit_minutes: int = Field(ge=1, le=300)
    order: int | None = Field(default=None, ge=0)
    passages: list[PassageWrite] | None = None
    questions: list[QuestionWrite] | None = None


class ModuleUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1, le=300)
    order: int | None = Field(default=None, ge=0)


class ModuleStudentRead(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    time_limit_minutes: int
    order: int
    passages: list[PassageRead] = Field(default_factory=list)
    questions: list[QuestionStudentRead] = Field(default_factory=list)


class ModuleAdminRead(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    time_limit_minutes: int
    order: int
    passages: list[PassageRead] = Field(default_factory=list)
    questions: list[QuestionAdminRead] = Field(default_factory=list)


# ---------- Mocks ----------


class MockCreate(ORMModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    instructions: str | None = None
    kind: MockKind = MockKind.SAT_RW
    total_minutes: int = Field(default=64, ge=1, le=600)
    pass_percent: int = Field(default=60, ge=0, le=100)


class MockUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    instructions: str | None = None
    kind: MockKind | None = None
    total_minutes: int | None = Field(default=None, ge=1, le=600)
    pass_percent: int | None = Field(default=None, ge=0, le=100)
    status: MockStatus | None = None


class MockSummary(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    kind: MockKind
    total_minutes: int
    pass_percent: int
    status: MockStatus
    modules_count: int = 0
    questions_count: int = 0
    created_at: datetime


class MockStudentRead(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    instructions: str | None = None
    kind: MockKind
    total_minutes: int
    pass_percent: int
    modules: list[ModuleStudentRead] = Field(default_factory=list)


class MockAdminRead(ORMModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None = None
    instructions: str | None = None
    kind: MockKind
    total_minutes: int
    pass_percent: int
    status: MockStatus
    modules: list[ModuleAdminRead] = Field(default_factory=list)
    created_at: datetime
