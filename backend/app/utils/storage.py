from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationAppError

_ALLOWED = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


async def save_upload(file: UploadFile, *, subdir: str) -> tuple[str, int]:
    if file.content_type not in _ALLOWED:
        raise ValidationAppError(
            f"Unsupported content type {file.content_type}", code="unsupported_media"
        )
    data = await file.read()
    size = len(data)
    if size > _MAX_BYTES:
        raise ValidationAppError("File too large (max 5 MB)", code="file_too_large")
    suffix = Path(file.filename or "").suffix.lower() or ".bin"
    name = f"{uuid.uuid4().hex}{suffix}"
    key = f"{subdir.strip('/')}/{name}"

    if settings.STORAGE_BACKEND == "local":
        root = Path(settings.MEDIA_DIR)
        target = root / key
        _ensure_dir(target.parent)
        target.write_bytes(data)
        return key, size

    # S3 backend stub — actual upload should use aioboto3 in production.
    raise NotImplementedError("S3 backend not configured")


def media_url(key: str | None) -> str | None:
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key
    if settings.STORAGE_BACKEND == "s3" and settings.AWS_S3_PUBLIC_BASE_URL:
        return f"{settings.AWS_S3_PUBLIC_BASE_URL.rstrip('/')}/{key.lstrip('/')}"
    return f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{key.lstrip('/')}"


def media_root() -> Path:
    return Path(settings.MEDIA_DIR).resolve()
