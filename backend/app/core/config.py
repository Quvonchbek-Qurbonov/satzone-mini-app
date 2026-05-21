from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    LOG_JSON: bool = False
    APP_NAME: str = "satzone-miniapp"
    API_V1_PREFIX: str = "/api/v1"

    # Mini-app DB
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5434
    POSTGRES_USER: str = "miniapp"
    POSTGRES_PASSWORD: str = "miniapp"
    POSTGRES_DB: str = "miniapp"

    # Satzone DB (read-only)
    SATZONE_DB_HOST: str = "localhost"
    SATZONE_DB_PORT: int = 5433
    SATZONE_DB_USER: str = "miniapp_ro"
    SATZONE_DB_PASSWORD: str = ""
    SATZONE_DB_NAME: str = "satzone"

    # Satzone admin API
    SATZONE_API_BASE: str = "http://localhost:8080/api/v1"
    SATZONE_ADMIN_TOKEN: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_INIT_DATA_TTL_SECONDS: int = 86400

    # Admin allowlist (comma-separated E.164)
    ADMIN_PHONES: str = ""

    # Auth
    JWT_SECRET: str = ""
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 900
    REFRESH_TOKEN_TTL_DAYS: int = 14

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6380
    REDIS_DB: int = 0

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    MEDIA_DIR: str = "./media"
    MEDIA_URL_PREFIX: str = "/media"
    AWS_S3_BUCKET: str = ""
    AWS_S3_REGION: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_PUBLIC_BASE_URL: str = ""

    # CORS
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173"
    FRONTEND_URL: str = "http://localhost:5173"
    WEBSITE_URL: str = "https://your-website.example.com"

    # Rate limiting
    RATE_LIMIT_DEFAULT_PER_MIN: int = 120
    RATE_LIMIT_AUTH_PER_MIN: int = 20

    # Submission timer grace (server allows the client a small fudge factor)
    SUBMISSION_GRACE_SECONDS: int = 10

    @field_validator("ADMIN_PHONES", mode="before")
    @classmethod
    def _strip_admin_phones(cls, v: str | None) -> str:
        return (v or "").strip()

    @property
    def admin_phone_set(self) -> set[str]:
        return {p.strip() for p in self.ADMIN_PHONES.split(",") if p.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def satzone_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.SATZONE_DB_USER}:{self.SATZONE_DB_PASSWORD}"
            f"@{self.SATZONE_DB_HOST}:{self.SATZONE_DB_PORT}/{self.SATZONE_DB_NAME}"
        )

    def assert_production_ready(self) -> None:
        if self.ENV != "production":
            return
        missing = [
            name
            for name, value in {
                "JWT_SECRET": self.JWT_SECRET,
                "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
                "SATZONE_DB_PASSWORD": self.SATZONE_DB_PASSWORD,
                "POSTGRES_PASSWORD": self.POSTGRES_PASSWORD,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"production env requires: {', '.join(missing)}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.assert_production_ready()
    return s


settings = get_settings()
