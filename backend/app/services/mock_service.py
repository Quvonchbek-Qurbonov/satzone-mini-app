from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.enums import MockStatus, QuestionType
from app.models.mock import (
    Mock,
    MockModule,
    MockOption,
    MockPassage,
    MockQuestion,
)
from app.models.user import MiniAppUser
from app.schemas.mock import (
    MockCreate,
    MockUpdate,
    ModuleUpdate,
    ModuleWrite,
    PassageWrite,
    QuestionUpdate,
    QuestionWrite,
)
from app.utils.storage import media_url


# ---------- Loaders ----------


def _full_mock_loader():
    return (
        selectinload(Mock.modules)
        .selectinload(MockModule.passages),
        selectinload(Mock.modules)
        .selectinload(MockModule.questions)
        .selectinload(MockQuestion.options),
    )


async def get_mock_or_404(
    session: AsyncSession, mock_id: uuid.UUID, *, eager: bool = True
) -> Mock:
    stmt = select(Mock).where(Mock.id == mock_id)
    if eager:
        stmt = stmt.options(*_full_mock_loader())
    mock = (await session.execute(stmt)).unique().scalar_one_or_none()
    if mock is None:
        raise NotFoundError("Mock not found", code="mock_not_found")
    return mock


async def get_published_mock_for_student(
    session: AsyncSession, mock_id: uuid.UUID
) -> Mock:
    mock = await get_mock_or_404(session, mock_id)
    if mock.status != MockStatus.PUBLISHED:
        raise NotFoundError("Mock not found", code="mock_not_found")
    return mock


async def list_mocks_for_course(
    session: AsyncSession,
    course_id: uuid.UUID,
    *,
    include_drafts: bool = False,
) -> list[Mock]:
    stmt = (
        select(Mock)
        .where(Mock.course_id == course_id)
        .order_by(Mock.created_at.desc())
        .options(*_full_mock_loader())
    )
    if not include_drafts:
        stmt = stmt.where(Mock.status == MockStatus.PUBLISHED)
    return list((await session.execute(stmt)).unique().scalars().all())


async def count_published_mocks_by_course(
    session: AsyncSession, course_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not course_ids:
        return {}
    stmt = (
        select(Mock.course_id, func.count(Mock.id))
        .where(Mock.course_id.in_(course_ids), Mock.status == MockStatus.PUBLISHED)
        .group_by(Mock.course_id)
    )
    return dict((await session.execute(stmt)).all())


# ---------- Mock CRUD ----------


async def create_mock(
    session: AsyncSession, payload: MockCreate, author: MiniAppUser
) -> Mock:
    mock = Mock(
        course_id=payload.course_id,
        title=payload.title.strip(),
        description=payload.description,
        instructions=payload.instructions,
        kind=payload.kind,
        total_minutes=payload.total_minutes,
        pass_percent=payload.pass_percent,
        status=MockStatus.DRAFT,
        created_by=author.id,
    )
    session.add(mock)
    await session.commit()
    return await get_mock_or_404(session, mock.id)


async def update_mock(
    session: AsyncSession, mock_id: uuid.UUID, payload: MockUpdate
) -> Mock:
    mock = await get_mock_or_404(session, mock_id, eager=False)
    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()
    for k, v in data.items():
        setattr(mock, k, v)
    await session.commit()
    return await get_mock_or_404(session, mock.id)


async def delete_mock(session: AsyncSession, mock_id: uuid.UUID) -> None:
    mock = await get_mock_or_404(session, mock_id, eager=False)
    await session.delete(mock)
    await session.commit()


# ---------- Modules ----------


async def _next_order(session: AsyncSession, *, parent_attr, parent_id, model) -> int:
    stmt = select(func.coalesce(func.max(model.order), -1) + 1).where(
        parent_attr == parent_id
    )
    return int((await session.execute(stmt)).scalar_one())


async def add_module(
    session: AsyncSession, mock_id: uuid.UUID, payload: ModuleWrite
) -> MockModule:
    mock = await get_mock_or_404(session, mock_id, eager=False)
    order = payload.order
    if order is None:
        order = await _next_order(
            session, parent_attr=MockModule.mock_id, parent_id=mock.id, model=MockModule
        )
    module = MockModule(
        mock_id=mock.id,
        title=payload.title.strip(),
        description=payload.description,
        time_limit_minutes=payload.time_limit_minutes,
        order=order,
    )
    session.add(module)
    await session.flush()

    if payload.passages:
        for p_idx, pw in enumerate(payload.passages):
            session.add(
                MockPassage(
                    module_id=module.id,
                    title=pw.title,
                    subtitle=pw.subtitle,
                    body_html=pw.body_html or "",
                    order=pw.order if pw.order is not None else p_idx,
                )
            )
    if payload.questions:
        for q_idx, qw in enumerate(payload.questions):
            await _create_question_in_module(
                session, module, qw, default_order=q_idx
            )

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "Module order conflict", code="order_conflict"
        ) from exc
    await session.refresh(module)
    return module


async def update_module(
    session: AsyncSession, module_id: uuid.UUID, payload: ModuleUpdate
) -> MockModule:
    module = await session.get(MockModule, module_id)
    if module is None:
        raise NotFoundError("Module not found", code="module_not_found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(module, k, v)
    await session.commit()
    await session.refresh(module)
    return module


async def delete_module(session: AsyncSession, module_id: uuid.UUID) -> None:
    module = await session.get(MockModule, module_id)
    if module is None:
        raise NotFoundError("Module not found", code="module_not_found")
    await session.delete(module)
    await session.commit()


# ---------- Passages ----------


async def add_passage(
    session: AsyncSession, module_id: uuid.UUID, payload: PassageWrite
) -> MockPassage:
    module = await session.get(MockModule, module_id)
    if module is None:
        raise NotFoundError("Module not found", code="module_not_found")
    order = payload.order
    if order is None:
        order = await _next_order(
            session,
            parent_attr=MockPassage.module_id,
            parent_id=module.id,
            model=MockPassage,
        )
    passage = MockPassage(
        module_id=module.id,
        title=payload.title,
        subtitle=payload.subtitle,
        body_html=payload.body_html or "",
        order=order,
    )
    session.add(passage)
    await session.commit()
    await session.refresh(passage)
    return passage


async def update_passage(
    session: AsyncSession, passage_id: uuid.UUID, payload: PassageWrite
) -> MockPassage:
    passage = await session.get(MockPassage, passage_id)
    if passage is None:
        raise NotFoundError("Passage not found", code="passage_not_found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(passage, k, v)
    await session.commit()
    await session.refresh(passage)
    return passage


async def delete_passage(session: AsyncSession, passage_id: uuid.UUID) -> None:
    passage = await session.get(MockPassage, passage_id)
    if passage is None:
        raise NotFoundError("Passage not found", code="passage_not_found")
    await session.delete(passage)
    await session.commit()


# ---------- Questions ----------


async def _create_question_in_module(
    session: AsyncSession,
    module: MockModule,
    payload: QuestionWrite,
    *,
    default_order: int = 0,
) -> MockQuestion:
    order = payload.order if payload.order is not None else default_order
    if payload.passage_id is not None:
        passage = await session.get(MockPassage, payload.passage_id)
        if passage is None or passage.module_id != module.id:
            raise ValidationAppError(
                "passage_id does not belong to this module",
                code="passage_module_mismatch",
            )
    q = MockQuestion(
        module_id=module.id,
        passage_id=payload.passage_id,
        type=payload.type,
        prompt=payload.prompt,
        explanation=payload.explanation,
        image_url=payload.image_url,
        points=payload.points,
        order=order,
        expected_answers=payload.expected_answers,
    )
    session.add(q)
    await session.flush()

    if payload.options:
        for idx, opt in enumerate(payload.options):
            session.add(
                MockOption(
                    question_id=q.id,
                    text=opt.text,
                    is_correct=opt.is_correct,
                    order=opt.order if opt.order is not None else idx,
                    image_url=opt.image_url,
                )
            )
    return q


async def add_question(
    session: AsyncSession,
    module_id: uuid.UUID,
    payload: QuestionWrite,
) -> MockQuestion:
    module = await session.get(MockModule, module_id)
    if module is None:
        raise NotFoundError("Module not found", code="module_not_found")
    next_order = await _next_order(
        session,
        parent_attr=MockQuestion.module_id,
        parent_id=module.id,
        model=MockQuestion,
    )
    q = await _create_question_in_module(
        session, module, payload, default_order=next_order
    )
    await session.commit()
    return (
        await session.execute(
            select(MockQuestion)
            .where(MockQuestion.id == q.id)
            .options(selectinload(MockQuestion.options))
        )
    ).scalar_one()


async def update_question(
    session: AsyncSession,
    question_id: uuid.UUID,
    payload: QuestionUpdate,
) -> MockQuestion:
    q = (
        await session.execute(
            select(MockQuestion)
            .where(MockQuestion.id == question_id)
            .options(selectinload(MockQuestion.options))
        )
    ).scalar_one_or_none()
    if q is None:
        raise NotFoundError("Question not found", code="question_not_found")

    data = payload.model_dump(exclude_unset=True, exclude={"options"})
    if "passage_id" in data and data["passage_id"] is not None:
        passage = await session.get(MockPassage, data["passage_id"])
        if passage is None or passage.module_id != q.module_id:
            raise ValidationAppError(
                "passage_id does not belong to this module",
                code="passage_module_mismatch",
            )
    for k, v in data.items():
        setattr(q, k, v)

    if payload.options is not None:
        # Replace options wholesale — simplest semantics for editors.
        for existing in list(q.options):
            await session.delete(existing)
        await session.flush()
        for idx, opt in enumerate(payload.options):
            session.add(
                MockOption(
                    question_id=q.id,
                    text=opt.text,
                    is_correct=opt.is_correct,
                    order=opt.order if opt.order is not None else idx,
                    image_url=opt.image_url,
                )
            )
        # Re-validate counts/correctness using the QuestionWrite rules.
        if q.type == QuestionType.SINGLE_CHOICE:
            correct = sum(1 for o in payload.options if o.is_correct)
            if correct != 1:
                await session.rollback()
                raise ValidationAppError(
                    "single_choice must have exactly one correct option",
                    code="invalid_options",
                )
        elif q.type == QuestionType.MULTI_CHOICE:
            if not any(o.is_correct for o in payload.options):
                await session.rollback()
                raise ValidationAppError(
                    "multi_choice needs at least one correct option",
                    code="invalid_options",
                )

    await session.commit()
    return (
        await session.execute(
            select(MockQuestion)
            .where(MockQuestion.id == question_id)
            .options(selectinload(MockQuestion.options))
        )
    ).scalar_one()


async def delete_question(session: AsyncSession, question_id: uuid.UUID) -> None:
    q = await session.get(MockQuestion, question_id)
    if q is None:
        raise NotFoundError("Question not found", code="question_not_found")
    await session.delete(q)
    await session.commit()


async def set_question_image(
    session: AsyncSession, question_id: uuid.UUID, key: str
) -> str:
    q = await session.get(MockQuestion, question_id)
    if q is None:
        raise NotFoundError("Question not found", code="question_not_found")
    q.image_url = key
    await session.commit()
    return media_url(key) or ""
