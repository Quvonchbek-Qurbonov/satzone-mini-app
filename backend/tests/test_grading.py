"""Pure-function tests for the grading logic. No DB required."""

from __future__ import annotations

import os
import uuid

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "x")
os.environ.setdefault("SATZONE_DB_PASSWORD", "x")


class _Q:
    """Lightweight stand-in for ``MockQuestion`` so we don't need the DB."""

    def __init__(
        self,
        type,  # noqa: A002
        options,
        points=1,
        expected_answers=None,
    ):
        self.type = type
        self.options = options
        self.points = points
        self.expected_answers = expected_answers


class _Opt:
    def __init__(self, is_correct: bool):
        self.id = uuid.uuid4()
        self.is_correct = is_correct


def test_single_choice_correct():
    from app.models.enums import QuestionType
    from app.services.attempt_service import _grade_question

    correct = _Opt(True)
    other = _Opt(False)
    q = _Q(QuestionType.SINGLE_CHOICE, [correct, other], points=2)
    ok, pts = _grade_question(q, {"selected_option_ids": [str(correct.id)]})
    assert ok is True
    assert pts == 2


def test_single_choice_wrong():
    from app.models.enums import QuestionType
    from app.services.attempt_service import _grade_question

    correct = _Opt(True)
    other = _Opt(False)
    q = _Q(QuestionType.SINGLE_CHOICE, [correct, other])
    ok, pts = _grade_question(q, {"selected_option_ids": [str(other.id)]})
    assert ok is False
    assert pts == 0


def test_multi_choice_partial_not_credited():
    from app.models.enums import QuestionType
    from app.services.attempt_service import _grade_question

    a = _Opt(True)
    b = _Opt(True)
    c = _Opt(False)
    q = _Q(QuestionType.MULTI_CHOICE, [a, b, c])
    ok, pts = _grade_question(q, {"selected_option_ids": [str(a.id)]})
    assert ok is False
    assert pts == 0
    ok2, pts2 = _grade_question(q, {"selected_option_ids": [str(a.id), str(b.id)]})
    assert ok2 is True
    assert pts2 == 1


def test_grid_in_normalization():
    from app.models.enums import QuestionType
    from app.services.attempt_service import _grade_question

    q = _Q(QuestionType.GRID_IN, [], expected_answers=["3/4", "0.75"])
    assert _grade_question(q, {"text": "3/4"})[0] is True
    assert _grade_question(q, {"text": "0.75"})[0] is True
    assert _grade_question(q, {"text": " 0.75 "})[0] is True
    assert _grade_question(q, {"text": "0.8"})[0] is False
    assert _grade_question(q, None)[0] is False
