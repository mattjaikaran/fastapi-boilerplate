from fastapi import APIRouter, BackgroundTasks, Request

from app.api.auth.dependencies import CurrentUser
from app.api.auth.model import OTPPurpose
from app.api.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RequestOTPRequest,
    ResetPasswordRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TokenResponse,
    VerifyOTPRequest,
)
from app.api.auth.service import AuthService
from app.api.users.schemas import UserResponse
from app.config.database import DBSession
from app.core.exceptions.auth import InvalidCredentialsError
from app.core.security import get_password_hash, verify_password
from app.services.cache import get_cache_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(db: DBSession) -> AuthService:
    from app.services.cache import CacheService

    cache = CacheService()
    return AuthService(db=db, cache=cache)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: DBSession) -> AuthResponse:
    return await _get_auth_service(db).register(body)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request, db: DBSession) -> AuthResponse:
    service = _get_auth_service(db)
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None
    return await service.login(body, user_agent=user_agent, ip_address=ip_address)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    return await _get_auth_service(db).refresh(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshTokenRequest, db: DBSession) -> MessageResponse:
    await _get_auth_service(db).logout(body.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.post("/request-otp", response_model=MessageResponse)
async def request_otp(body: RequestOTPRequest, db: DBSession) -> MessageResponse:
    purpose = OTPPurpose(body.purpose)
    await _get_auth_service(db).request_otp(body.email, purpose)
    return MessageResponse(message="OTP sent if email is registered")


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(body: VerifyOTPRequest, db: DBSession) -> MessageResponse:
    purpose = OTPPurpose(body.purpose)
    await _get_auth_service(db).verify_otp(body.email, body.code, purpose)
    return MessageResponse(message="OTP verified successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, db: DBSession) -> MessageResponse:
    await _get_auth_service(db).forgot_password(body.email)
    return MessageResponse(message="Reset code sent if email is registered")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: DBSession) -> MessageResponse:
    # body.token is "email:code"
    parts = body.token.split(":", 1)
    if len(parts) != 2:
        raise InvalidCredentialsError(detail="Invalid reset token format")
    email, code = parts
    await _get_auth_service(db).reset_password(email, code, body.new_password)
    return MessageResponse(message="Password reset successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest, current_user: CurrentUser, db: DBSession
) -> MessageResponse:
    if not current_user.hashed_password or not verify_password(
        body.current_password, current_user.hashed_password
    ):
        raise InvalidCredentialsError(detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(body.new_password)
    db.add(current_user)
    return MessageResponse(message="Password changed successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(current_user: CurrentUser, db: DBSession) -> TOTPSetupResponse:
    secret, uri = await _get_auth_service(db).setup_totp(current_user)
    return TOTPSetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/totp/verify", response_model=MessageResponse)
async def verify_totp(
    body: TOTPVerifyRequest, current_user: CurrentUser, db: DBSession
) -> MessageResponse:
    valid = await _get_auth_service(db).verify_totp(current_user, body.code)
    if not valid:
        raise InvalidCredentialsError(detail="Invalid TOTP code")
    return MessageResponse(message="TOTP enabled successfully")
