from __future__ import annotations

import math
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    size: int = 20


def page_params(
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, size=size)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


async def paginate(
    session: AsyncSession,
    stmt: Select,
    params: PageParams,
) -> tuple[list, int]:
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    offset = (params.page - 1) * params.size
    paged_stmt = stmt.offset(offset).limit(params.size)
    rows = (await session.execute(paged_stmt)).scalars().all()
    return list(rows), int(total)


def to_page(items: list[T], total: int, params: PageParams) -> Page[T]:
    pages = math.ceil(total / params.size) if total else 0
    return Page(items=items, total=total, page=params.page, size=params.size, pages=pages)
