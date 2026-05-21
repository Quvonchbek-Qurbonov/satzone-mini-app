from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.core.exceptions import ForbiddenError
from app.db.session import DbSession
from app.models.enums import UserRole
from app.schemas.mock import (
    MockStudentRead,
    MockSummary,
    ModuleStudentRead,
    OptionStudentRead,
    PassageRead,
    QuestionStudentRead,
)
from app.services import mock_service, satzone_client
from app.utils.storage import media_url

router = APIRouter(tags=["mocks"])


def _passage_read(p) -> PassageRead:
    return PassageRead(
        id=p.id, title=p.title, subtitle=p.subtitle, body_html=p.body_html, order=p.order
    )


def _option_read(o) -> OptionStudentRead:
    return OptionStudentRead(
        id=o.id, text=o.text, order=o.order, image_url=media_url(o.image_url)
    )


def _question_read(q) -> QuestionStudentRead:
    return QuestionStudentRead(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        image_url=media_url(q.image_url),
        points=q.points,
        order=q.order,
        passage_id=q.passage_id,
        options=[_option_read(o) for o in q.options],
    )


def _module_read(m) -> ModuleStudentRead:
    return ModuleStudentRead(
        id=m.id,
        title=m.title,
        description=m.description,
        time_limit_minutes=m.time_limit_minutes,
        order=m.order,
        passages=[_passage_read(p) for p in m.passages],
        questions=[_question_read(q) for q in m.questions],
    )


def _summary(mock) -> MockSummary:
    q_count = sum(len(m.questions) for m in mock.modules)
    return MockSummary(
        id=mock.id,
        course_id=mock.course_id,
        title=mock.title,
        description=mock.description,
        kind=mock.kind,
        total_minutes=mock.total_minutes,
        pass_percent=mock.pass_percent,
        status=mock.status,
        modules_count=len(mock.modules),
        questions_count=q_count,
        created_at=mock.created_at,
    )


@router.get("/courses/{course_id}/mocks", response_model=list[MockSummary])
async def list_course_mocks(
    course_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> list[MockSummary]:
    if user.role != UserRole.ADMIN:
        if user.satzone_user_id is None:
            raise ForbiddenError("Not linked", code="not_linked")
        enrolled = await satzone_client.list_user_course_ids(user.satzone_user_id)
        if course_id not in enrolled:
            raise ForbiddenError("Not enrolled", code="not_enrolled")
    mocks = await mock_service.list_mocks_for_course(
        session, course_id, include_drafts=(user.role == UserRole.ADMIN)
    )
    return [_summary(m) for m in mocks]


@router.get("/mocks/{mock_id}", response_model=MockStudentRead)
async def get_mock(
    mock_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> MockStudentRead:
    if user.role == UserRole.ADMIN:
        mock = await mock_service.get_mock_or_404(session, mock_id)
    else:
        mock = await mock_service.get_published_mock_for_student(session, mock_id)
        if user.satzone_user_id is None:
            raise ForbiddenError("Not linked", code="not_linked")
        enrolled = await satzone_client.list_user_course_ids(user.satzone_user_id)
        if mock.course_id not in enrolled:
            raise ForbiddenError("Not enrolled", code="not_enrolled")

    return MockStudentRead(
        id=mock.id,
        course_id=mock.course_id,
        title=mock.title,
        description=mock.description,
        instructions=mock.instructions,
        kind=mock.kind,
        total_minutes=mock.total_minutes,
        pass_percent=mock.pass_percent,
        modules=[_module_read(m) for m in mock.modules],
    )
