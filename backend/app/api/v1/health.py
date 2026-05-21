from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import DbSession, engine
from app.middleware.rate_limit import _get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: DbSession) -> dict:
    db_ok = True
    redis_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    try:
        await _get_redis().ping()
    except Exception:
        redis_ok = False
    status = "ready" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok}
