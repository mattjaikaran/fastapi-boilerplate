from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, EmailStr, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    APP_PORT: int = 8000
    APP_WORKERS: int = 1
    APP_LOG_LEVEL: str = "info"
    APP_VERSION: str = "0.1.0"

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

    # AI/ML
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ML_MODEL_PATH: str = "./models"
    ML_MAX_CONCURRENT_TASKS: int = 4

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
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
