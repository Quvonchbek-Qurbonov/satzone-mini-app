from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import admin, attempts, auth, courses, health, mocks

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(mocks.router)
api_router.include_router(attempts.router)
api_router.include_router(admin.router)
