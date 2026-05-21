from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class MockKind(str, Enum):
    SAT_RW = "sat_rw"
    SAT_MATH = "sat_math"
    GENERIC = "generic"


class MockStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    GRID_IN = "grid_in"
    SHORT_ANSWER = "short_answer"


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
