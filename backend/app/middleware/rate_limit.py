from __future__ import annotations

import time
from typing import Awaitable, Callable

import redis.asyncio as redis
from fastapi import Request, Response

from app.core.config import settings
from app.core.exceptions import RateLimitedError

_redis: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _redis


def _client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return (request.client.host if request.client else "unknown")


async def _allow(key: str, limit: int, window_seconds: int = 60) -> bool:
    r = _get_redis()
    bucket = int(time.time() // window_seconds)
    redis_key = f"rl:{key}:{bucket}"
    try:
        count = await r.incr(redis_key)
        if count == 1:
            await r.expire(redis_key, window_seconds + 5)
    except redis.RedisError:
        # Fail open if Redis is unavailable — better than locking everyone out.
        return True
    return count <= limit


async def rate_limit_default(request: Request) -> None:
    ip = _client_ip(request)
    if not await _allow(f"def:{ip}", settings.RATE_LIMIT_DEFAULT_PER_MIN):
        raise RateLimitedError(
            "Too many requests",
            details={"limit": settings.RATE_LIMIT_DEFAULT_PER_MIN, "window_seconds": 60},
        )


async def rate_limit_auth(request: Request) -> None:
    ip = _client_ip(request)
    path = request.url.path
    if not await _allow(f"auth:{ip}:{path}", settings.RATE_LIMIT_AUTH_PER_MIN):
        raise RateLimitedError(
            "Too many auth attempts",
            details={"limit": settings.RATE_LIMIT_AUTH_PER_MIN, "window_seconds": 60},
        )
