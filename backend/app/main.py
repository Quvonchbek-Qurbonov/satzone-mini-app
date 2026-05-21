from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    unexpected_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging, get_logger
from app.middleware.rate_limit import rate_limit_default
from app.middleware.request_id import RequestIDMiddleware

configure_logging()
logger = get_logger("main")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
        dependencies=[__rate_limit_dep__()],
    )

    if settings.STORAGE_BACKEND == "local":
        media_dir = Path(settings.MEDIA_DIR).resolve()
        media_dir.mkdir(parents=True, exist_ok=True)
        app.mount(
            settings.MEDIA_URL_PREFIX,
            StaticFiles(directory=str(media_dir)),
            name="media",
        )

    @app.on_event("startup")
    async def _startup() -> None:
        logger.info("app_startup", env=settings.ENV)

    return app


def __rate_limit_dep__():
    # Wrapped so we can keep the include_router call tidy.
    from fastapi import Depends

    return Depends(rate_limit_default)


app = create_app()
