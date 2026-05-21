from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.deps import CurrentAdmin
from app.db.session import DbSession
from app.schemas.base import Message
from app.schemas.course import CourseSummary
from app.schemas.mock import (
    MockAdminRead,
    MockCreate,
    MockUpdate,
    ModuleAdminRead,
    ModuleUpdate,
    ModuleWrite,
    OptionAdminRead,
    PassageRead,
    PassageWrite,
    QuestionAdminRead,
    QuestionUpdate,
    QuestionWrite,
)
from app.services import mock_service, satzone_client
from app.utils.storage import media_url, save_upload

router = APIRouter(prefix="/admin", tags=["admin"])


# ---- Serializers ----


def _option_admin(o) -> OptionAdminRead:
    return OptionAdminRead(
        id=o.id,
        text=o.text,
        order=o.order,
        image_url=media_url(o.image_url),
        is_correct=o.is_correct,
    )


def _passage_read(p) -> PassageRead:
    return PassageRead(
        id=p.id, title=p.title, subtitle=p.subtitle, body_html=p.body_html, order=p.order
    )


def _question_admin(q) -> QuestionAdminRead:
    return QuestionAdminRead(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        explanation=q.explanation,
        image_url=media_url(q.image_url),
        points=q.points,
        order=q.order,
        passage_id=q.passage_id,
        expected_answers=q.expected_answers,
        options=[_option_admin(o) for o in q.options],
    )


def _module_admin(m) -> ModuleAdminRead:
    return ModuleAdminRead(
        id=m.id,
        title=m.title,
        description=m.description,
        time_limit_minutes=m.time_limit_minutes,
        order=m.order,
        passages=[_passage_read(p) for p in m.passages],
        questions=[_question_admin(q) for q in m.questions],
    )


def _mock_admin(mock) -> MockAdminRead:
    return MockAdminRead(
        id=mock.id,
        course_id=mock.course_id,
        title=mock.title,
        description=mock.description,
        instructions=mock.instructions,
        kind=mock.kind,
        total_minutes=mock.total_minutes,
        pass_percent=mock.pass_percent,
        status=mock.status,
        modules=[_module_admin(m) for m in mock.modules],
        created_at=mock.created_at,
    )


# ---- Courses (catalog for authoring) ----


@router.get("/courses", response_model=list[CourseSummary])
async def list_courses(admin: CurrentAdmin, session: DbSession) -> list[CourseSummary]:
    courses = await satzone_client.list_courses()
    counts = await mock_service.count_published_mocks_by_course(
        session, [c.id for c in courses]
    )
    return [
        CourseSummary(
            course_id=c.id,
            title=c.title,
            slug=c.slug,
            thumbnail_url=c.thumbnail_url,
            instructor_name=c.instructor_name,
            mocks_count=counts.get(c.id, 0),
        )
        for c in courses
    ]


# ---- Mocks ----


@router.get("/mocks", response_model=list[MockAdminRead])
async def list_admin_mocks(
    admin: CurrentAdmin,
    session: DbSession,
    course_id: uuid.UUID | None = None,
) -> list[MockAdminRead]:
    if course_id is None:
        # All mocks across courses — admins use this rarely; in practice the
        # UI filters by course. Keep the result bounded.
        from sqlalchemy import select
        from app.models.mock import Mock
        from sqlalchemy.orm import selectinload
        from app.models.mock import MockModule, MockQuestion

        stmt = (
            select(Mock)
            .order_by(Mock.created_at.desc())
            .limit(200)
            .options(
                selectinload(Mock.modules).selectinload(MockModule.passages),
                selectinload(Mock.modules)
                .selectinload(MockModule.questions)
                .selectinload(MockQuestion.options),
            )
        )
        mocks = list((await session.execute(stmt)).unique().scalars().all())
    else:
        mocks = await mock_service.list_mocks_for_course(
            session, course_id, include_drafts=True
        )
    return [_mock_admin(m) for m in mocks]


@router.post(
    "/mocks",
    response_model=MockAdminRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_mock(
    payload: MockCreate, admin: CurrentAdmin, session: DbSession
) -> MockAdminRead:
    mock = await mock_service.create_mock(session, payload, admin)
    return _mock_admin(mock)


@router.get("/mocks/{mock_id}", response_model=MockAdminRead)
async def get_mock(
    mock_id: uuid.UUID, admin: CurrentAdmin, session: DbSession
) -> MockAdminRead:
    mock = await mock_service.get_mock_or_404(session, mock_id)
    return _mock_admin(mock)


@router.patch("/mocks/{mock_id}", response_model=MockAdminRead)
async def update_mock(
    mock_id: uuid.UUID,
    payload: MockUpdate,
    admin: CurrentAdmin,
    session: DbSession,
) -> MockAdminRead:
    mock = await mock_service.update_mock(session, mock_id, payload)
    return _mock_admin(mock)


@router.delete("/mocks/{mock_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_mock(
    mock_id: uuid.UUID, admin: CurrentAdmin, session: DbSession
) -> None:
    await mock_service.delete_mock(session, mock_id)


# ---- Modules ----


@router.post(
    "/mocks/{mock_id}/modules",
    response_model=ModuleAdminRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    mock_id: uuid.UUID,
    payload: ModuleWrite,
    admin: CurrentAdmin,
    session: DbSession,
) -> ModuleAdminRead:
    module = await mock_service.add_module(session, mock_id, payload)
    # Refresh with relations.
    from sqlalchemy import select
    from app.models.mock import MockModule, MockQuestion
    from sqlalchemy.orm import selectinload

    stmt = (
        select(MockModule)
        .where(MockModule.id == module.id)
        .options(
            selectinload(MockModule.passages),
            selectinload(MockModule.questions).selectinload(MockQuestion.options),
        )
    )
    full = (await session.execute(stmt)).scalar_one()
    return _module_admin(full)


@router.patch("/modules/{module_id}", response_model=ModuleAdminRead)
async def patch_module(
    module_id: uuid.UUID,
    payload: ModuleUpdate,
    admin: CurrentAdmin,
    session: DbSession,
) -> ModuleAdminRead:
    module = await mock_service.update_module(session, module_id, payload)
    from sqlalchemy import select
    from app.models.mock import MockModule, MockQuestion
    from sqlalchemy.orm import selectinload

    stmt = (
        select(MockModule)
        .where(MockModule.id == module.id)
        .options(
            selectinload(MockModule.passages),
            selectinload(MockModule.questions).selectinload(MockQuestion.options),
        )
    )
    full = (await session.execute(stmt)).scalar_one()
    return _module_admin(full)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_module(
    module_id: uuid.UUID, admin: CurrentAdmin, session: DbSession
) -> None:
    await mock_service.delete_module(session, module_id)


# ---- Passages ----


@router.post(
    "/modules/{module_id}/passages",
    response_model=PassageRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_passage(
    module_id: uuid.UUID,
    payload: PassageWrite,
    admin: CurrentAdmin,
    session: DbSession,
) -> PassageRead:
    p = await mock_service.add_passage(session, module_id, payload)
    return _passage_read(p)


@router.patch("/passages/{passage_id}", response_model=PassageRead)
async def patch_passage(
    passage_id: uuid.UUID,
    payload: PassageWrite,
    admin: CurrentAdmin,
    session: DbSession,
) -> PassageRead:
    p = await mock_service.update_passage(session, passage_id, payload)
    return _passage_read(p)


@router.delete("/passages/{passage_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_passage(
    passage_id: uuid.UUID, admin: CurrentAdmin, session: DbSession
) -> None:
    await mock_service.delete_passage(session, passage_id)


# ---- Questions ----


@router.post(
    "/modules/{module_id}/questions",
    response_model=QuestionAdminRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    module_id: uuid.UUID,
    payload: QuestionWrite,
    admin: CurrentAdmin,
    session: DbSession,
) -> QuestionAdminRead:
    q = await mock_service.add_question(session, module_id, payload)
    return _question_admin(q)


@router.patch("/questions/{question_id}", response_model=QuestionAdminRead)
async def patch_question(
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    admin: CurrentAdmin,
    session: DbSession,
) -> QuestionAdminRead:
    q = await mock_service.update_question(session, question_id, payload)
    return _question_admin(q)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_question(
    question_id: uuid.UUID, admin: CurrentAdmin, session: DbSession
) -> None:
    await mock_service.delete_question(session, question_id)


@router.post("/questions/{question_id}/image", response_model=Message)
async def upload_question_image(
    question_id: uuid.UUID,
    admin: CurrentAdmin,
    session: DbSession,
    file: UploadFile = File(...),
) -> Message:
    key, _size = await save_upload(file, subdir=f"questions/{question_id}")
    url = await mock_service.set_question_image(session, question_id, key)
    return Message(message=url)
