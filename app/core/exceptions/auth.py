from app.core.exceptions.base import AppError


class InvalidCredentialsError(AppError):
    status_code = 401
    error_code = "INVALID_CREDENTIALS"
    detail = "Invalid email or password"


class InvalidTokenError(AppError):
    status_code = 401
    error_code = "INVALID_TOKEN"
    detail = "Invalid or malformed token"


class TokenExpiredError(AppError):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    detail = "Token has expired"


class InvalidOTPError(AppError):
    status_code = 400
    error_code = "INVALID_OTP"
    detail = "Invalid or expired OTP"


class AccountLockedError(AppError):
    status_code = 423
    error_code = "ACCOUNT_LOCKED"
    detail = "Account is temporarily locked due to too many failed attempts"


class EmailNotVerifiedError(AppError):
    status_code = 403
    error_code = "EMAIL_NOT_VERIFIED"
    detail = "Email address has not been verified"
