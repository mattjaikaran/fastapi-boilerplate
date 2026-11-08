import tomllib
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DIST_NAME = "fastapi-postgres-boilerplate"
_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _project_version() -> str:
    """Return the version from pyproject.toml, the single source of truth.

    Use the installed package metadata first. Docker images sync with
    ``--no-install-project``, so fall back to reading pyproject.toml.
    """
    try:
        return metadata.version(_DIST_NAME)
    except metadata.PackageNotFoundError:
        pass
    try:
        with _PYPROJECT.open("rb") as f:
            return str(tomllib.load(f)["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0.0.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "FastAPI Postgres Boilerplate"
    APP_ENV: Literal["development", "production", "test"] = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8100
    APP_WORKERS: int = 1
    APP_LOG_LEVEL: str = "info"
    APP_VERSION: str = Field(default_factory=_project_version)

    # Security
    SECRET_KEY: str = Field(min_length=32)
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[AnyHttpUrl | str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "app_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300

    # JWT
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OTP
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Email
    RESEND_API_KEY: str = ""
    EMAIL_FROM: EmailStr = "noreply@example.com"
    EMAIL_FROM_NAME: str = "App"

    # Storage
    STORAGE_DRIVER: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_SIZE_MB: int = 50
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""
    AWS_S3_ENDPOINT_URL: str | None = None

    # Observability
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "fastapi-app"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    PROMETHEUS_ENABLED: bool = True

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # WebAuthn
    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_RP_NAME: str = "FastAPI App"
    WEBAUTHN_ORIGIN: str = "http://localhost:3000"

    # Admin
    FIRST_SUPERUSER_EMAIL: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changeme"

    # OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    OAUTH_REDIRECT_FRONTEND_URL: str = "http://localhost:3000/auth/callback"

    # Stripe
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_DEFAULT_PRICE_ID: str = ""

    # RabbitMQ (optional — install with `uv sync --extra mq`)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "platform.events"

    # AI/ML
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ML_MODEL_PATH: str = "./models"
    ML_MAX_CONCURRENT_TASKS: int = 4

    # Agents
    AGENT_DEFAULT_MODEL: str = "claude-sonnet-4-6"
    AGENT_MAX_STEPS: int = 10
    AGENT_TIMEOUT_SECONDS: int = 60
    # Neo4j (optional graph database; requires the `graph` extra)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    # Integrations
    NINJA_BASE_URL: str = "http://localhost:8000/api"
    NINJA_API_KEY: str = ""
    NINJA_TIMEOUT_SECONDS: float = 10.0

    @computed_field
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @computed_field
    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @computed_field
    @property
    def upload_max_size_bytes(self) -> int:
        return self.UPLOAD_MAX_SIZE_MB * 1024 * 1024

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.is_production:
            if self.SECRET_KEY == "change-me-to-a-random-64-char-string-in-production":
                raise ValueError("SECRET_KEY must be changed in production")
            if self.JWT_SECRET_KEY == "change-me-jwt-secret-key":
                raise ValueError("JWT_SECRET_KEY must be changed in production")
            if self.WEBAUTHN_RP_ID in ("localhost", "127.0.0.1"):
                raise ValueError(
                    "WEBAUTHN_RP_ID must be set to your production domain (not localhost)"
                )
            if self.WEBAUTHN_ORIGIN.startswith("http://"):
                raise ValueError("WEBAUTHN_ORIGIN must use https:// in production")
        return self

    # Vector database (optional pgvector)
    VECTOR_DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/app_db"
    )
    EMBEDDING_DIMENSIONS: int = 1536


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
