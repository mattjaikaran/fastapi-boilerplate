import structlog
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError

from app.core.exceptions.base import AppError

logger = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> ORJSONResponse:
        await logger.awarning("app_error", error_code=exc.error_code, detail=exc.detail)
        return ORJSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(
        _: Request, exc: PydanticValidationError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=422,
            content={"error": "VALIDATION_ERROR", "detail": exc.errors()},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_: Request, exc: IntegrityError) -> ORJSONResponse:
        await logger.awarning("db_integrity_error", error=str(exc))
        return ORJSONResponse(
            status_code=409,
            content={"error": "CONFLICT", "detail": "Resource already exists"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> ORJSONResponse:
        await logger.aerror("unhandled_exception", error=str(exc), exc_info=True)
        return ORJSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "detail": "An unexpected error occurred"},
        )
