from app.core.exceptions.base import AppError


class NotFoundError(AppError):
    status_code = 404
    error_code = "NOT_FOUND"
    detail = "Resource not found"


class ConflictError(AppError):
    status_code = 409
    error_code = "CONFLICT"
    detail = "Resource already exists"


class UnauthorizedError(AppError):
    status_code = 401
    error_code = "UNAUTHORIZED"
    detail = "Authentication required"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "FORBIDDEN"
    detail = "Access denied"


class ValidationError(AppError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    detail = "Validation failed"


class UnprocessableError(AppError):
    status_code = 422
    error_code = "UNPROCESSABLE"
    detail = "Request cannot be processed"


class RateLimitError(AppError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Too many requests"
