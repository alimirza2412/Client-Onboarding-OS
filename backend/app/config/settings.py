"""
Application configuration.

All configuration is read from environment variables (optionally via a
local .env file during development). Nothing environment-specific or
secret is hardcoded here — only safe local-development defaults so the
app can start without any setup.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # General
    app_name: str = "Client Onboarding OS API"
    environment: str = "development"
    debug: bool = True

    # Database
    # NOTE: No tables are created against this yet. This only wires up the
    # connection configuration so Phase 1 can start creating models and
    # running Alembic migrations against it.
    database_url: str = (
        "postgresql+psycopg2://postgres:postgres@localhost:5432/onboarding_os"
    )

    # Frontend origins allowed to call this API in development
    cors_origins: str = "http://localhost:3000"

    # Auth (JWT). SECRET_KEY has a demo-only default — override it in .env
    # for anything beyond local demo use.
    secret_key: str = "demo-only-secret-key-change-me-before-real-use"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h — convenient for a demo session

    # Temporal (decision B1: code-defined workflows, no visual builder)
    temporal_address: str = "127.0.0.1:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "onboarding-task-queue"

    # AI (Groq). If unset, the AI service falls back to a deterministic
    # mock extraction so the demo works without a live API key.
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"

    # File storage — local disk for the demo instead of S3/MinIO
    # (see docs/decisions.md). Path is relative to backend/ unless absolute.
    uploads_dir: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
