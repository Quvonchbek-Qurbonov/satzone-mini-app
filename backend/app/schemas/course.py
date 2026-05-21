from __future__ import annotations

import uuid

from pydantic import BaseModel


class CourseSummary(BaseModel):
    course_id: uuid.UUID
    title: str
    slug: str | None = None
    thumbnail_url: str | None = None
    instructor_name: str | None = None
    mocks_count: int = 0
    enrolled: bool = True
