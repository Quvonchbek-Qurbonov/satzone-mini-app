from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.db.session import DbSession
from app.models.enums import UserRole
from app.schemas.course import CourseSummary
from app.services import mock_service, satzone_client

router = APIRouter(tags=["courses"])


@router.get("/me/courses", response_model=list[CourseSummary])
async def list_my_courses(
    user: CurrentUser, session: DbSession
) -> list[CourseSummary]:
    """Courses the current user owns (or all, for admins), enriched with mock counts."""
    if user.role == UserRole.ADMIN:
        # Admin sees every published course so they can author mocks for any.
        sat_courses = await satzone_client.list_courses()
    else:
        if user.satzone_user_id is None:
            return []
        sat_courses = await satzone_client.list_user_courses(user.satzone_user_id)

    counts = await mock_service.count_published_mocks_by_course(
        session, [c.id for c in sat_courses]
    )

    items = [
        CourseSummary(
            course_id=c.id,
            title=c.title,
            slug=c.slug,
            thumbnail_url=c.thumbnail_url,
            instructor_name=c.instructor_name,
            mocks_count=counts.get(c.id, 0),
            enrolled=True,
        )
        for c in sat_courses
    ]

    # Students see only courses where mocks exist; admins see all.
    if user.role != UserRole.ADMIN:
        items = [it for it in items if it.mocks_count > 0]
    return items
