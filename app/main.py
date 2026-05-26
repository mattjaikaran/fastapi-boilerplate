import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.config.settings import settings
from app.core.exceptions.handlers import register_exception_handlers
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.APP_DEBUG,
        default_response_class=ORJSONResponse,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    _register_middleware(app)
    _register_routers(app)
    _register_events(app)
    register_exception_handlers(app)

    if settings.PROMETHEUS_ENABLED:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    return app


def _register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ORIGINS],
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_routers(app: FastAPI) -> None:
    from app.api.router import api_router
    from app.admin.setup import setup_admin

    app.include_router(api_router)
    # Add session middleware required by sqladmin
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    setup_admin(app)


def _register_events(app: FastAPI) -> None:
    @app.on_event("startup")
    async def on_startup() -> None:
        _configure_logging()
        if settings.OTEL_ENABLED:
            _configure_otel()
        if settings.SENTRY_DSN:
            _configure_sentry()
        await logger.ainfo("app_started", env=settings.APP_ENV, version=settings.APP_VERSION)

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        from app.config.database import engine

        await engine.dispose()
        await logger.ainfo("app_stopped")


def _configure_logging() -> None:
    import logging

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.is_development else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.APP_LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def _configure_otel() -> None:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()


def _configure_sentry() -> None:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
    )


app = create_app()
