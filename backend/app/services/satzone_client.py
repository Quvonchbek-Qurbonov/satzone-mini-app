"""Cross-service reads against the satzone backend.

Two surfaces:

* Read-only SQL through the ``miniapp_ro`` Postgres role (defined in
  ``ops/satzone-ro.sql``). We use this for the phone → user lookup because
  satzone's admin API does not expose phone numbers in ``AdminUserRead``.
* Bearer-token HTTP calls to the admin API for enrollments / course detail.

Neither surface mutates satzone state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.db.satzone_read import get_satzone_session

logger = get_logger(__name__)


@dataclass(frozen=True)
class SatzoneUser:
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_phone_verified: bool


@dataclass(frozen=True)
class SatzoneCourse:
    id: uuid.UUID
    title: str
    slug: str | None
    thumbnail_url: str | None
    instructor_name: str | None


async def find_user_by_phone(phone_number: str) -> SatzoneUser | None:
    """Lookup a user in satzone by E.164 phone. None if not found.

    Runs as the ``miniapp_ro`` role which holds ``SELECT`` only — write
    attempts raise at the Postgres layer.
    """
    sql = text(
        "SELECT id, email, full_name, is_active, is_phone_verified "
        "FROM users WHERE phone_number = :phone LIMIT 1"
    )
    async for session in get_satzone_session():
        try:
            result = await session.execute(sql, {"phone": phone_number})
        except Exception as exc:  # connection / role error
            logger.error("satzone_phone_lookup_failed", error=str(exc))
            raise AppError(
                "Could not reach the main platform — please try again",
                code="satzone_unavailable",
                status_code=503,
            ) from exc
        row = result.first()
        if row is None:
            return None
        return SatzoneUser(
            id=row.id,
            email=row.email,
            full_name=row.full_name or "",
            is_active=bool(row.is_active),
            is_phone_verified=bool(row.is_phone_verified),
        )
    return None


async def get_course(course_id: uuid.UUID) -> SatzoneCourse | None:
    """Lookup a satzone course by id via read-only SQL.

    Reads from ``courses`` + ``instructors`` (joined) without touching
    enrollments. Returns None if the course was removed.
    """
    sql = text(
        """
        SELECT c.id, c.title, c.slug, c.thumbnail_url, i.full_name AS instructor_name
        FROM courses c
        LEFT JOIN instructors i ON i.id = c.instructor_id
        WHERE c.id = :id
        LIMIT 1
        """
    )
    async for session in get_satzone_session():
        try:
            result = await session.execute(sql, {"id": course_id})
        except Exception as exc:
            logger.error("satzone_course_lookup_failed", error=str(exc))
            return None
        row = result.first()
        if row is None:
            return None
        return SatzoneCourse(
            id=row.id,
            title=row.title or "",
            slug=row.slug,
            thumbnail_url=row.thumbnail_url,
            instructor_name=row.instructor_name,
        )
    return None


async def list_courses(*, limit: int = 500) -> list[SatzoneCourse]:
    """All published courses — used by admin authoring UI."""
    sql = text(
        """
        SELECT c.id, c.title, c.slug, c.thumbnail_url, i.full_name AS instructor_name
        FROM courses c
        LEFT JOIN instructors i ON i.id = c.instructor_id
        WHERE c.status = 'published'
        ORDER BY c.created_at DESC
        LIMIT :limit
        """
    )
    async for session in get_satzone_session():
        try:
            result = await session.execute(sql, {"limit": limit})
        except Exception as exc:
            logger.error("satzone_courses_list_failed", error=str(exc))
            return []
        rows = result.all()
        return [
            SatzoneCourse(
                id=r.id,
                title=r.title or "",
                slug=r.slug,
                thumbnail_url=r.thumbnail_url,
                instructor_name=r.instructor_name,
            )
            for r in rows
        ]
    return []


async def list_user_course_ids(user_id: uuid.UUID) -> list[uuid.UUID]:
    """All course IDs a user is enrolled in (active + completed).

    Reads enrollments directly. The admin API ``GET /admin/enrollments``
    would also work; we choose direct SQL for latency and to avoid
    juggling a long-lived service-account token. Add the token-based path
    later if direct DB access is undesirable.
    """
    sql = text(
        "SELECT course_id FROM enrollments WHERE user_id = :uid"
    )
    async for session in get_satzone_session():
        try:
            result = await session.execute(sql, {"uid": user_id})
        except Exception as exc:
            logger.error("satzone_enrollments_list_failed", error=str(exc))
            return []
        return [row.course_id for row in result.all()]
    return []


async def list_user_courses(user_id: uuid.UUID) -> list[SatzoneCourse]:
    """Convenience: enrolled course IDs joined with course metadata."""
    sql = text(
        """
        SELECT c.id, c.title, c.slug, c.thumbnail_url, i.full_name AS instructor_name
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        LEFT JOIN instructors i ON i.id = c.instructor_id
        WHERE e.user_id = :uid
        ORDER BY e.enrolled_at DESC
        """
    )
    async for session in get_satzone_session():
        try:
            result = await session.execute(sql, {"uid": user_id})
        except Exception as exc:
            logger.error("satzone_user_courses_failed", error=str(exc))
            return []
        return [
            SatzoneCourse(
                id=r.id,
                title=r.title or "",
                slug=r.slug,
                thumbnail_url=r.thumbnail_url,
                instructor_name=r.instructor_name,
            )
            for r in result.all()
        ]
    return []


# ---- HTTP admin-API fallback (kept for parity / future use) ----


async def admin_get(path: str, params: dict | None = None) -> dict | None:
    """GET helper for the satzone admin API. Returns parsed JSON or None."""
    if not settings.SATZONE_ADMIN_TOKEN:
        return None
    url = f"{settings.SATZONE_API_BASE.rstrip('/')}{path}"
    headers = {"Authorization": f"Bearer {settings.SATZONE_ADMIN_TOKEN}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(url, params=params or {}, headers=headers)
        except httpx.HTTPError as exc:
            logger.warning("satzone_admin_api_failed", path=path, error=str(exc))
            return None
    if r.status_code >= 400:
        logger.warning(
            "satzone_admin_api_error", path=path, status=r.status_code
        )
        return None
    try:
        return r.json()
    except ValueError:
        return None
