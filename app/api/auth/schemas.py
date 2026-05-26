from pydantic import BaseModel, EmailStr, Field

from app.api.users.schemas import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


class RequestOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "email_verification"


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    purpose: str = "email_verification"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MessageResponse(BaseModel):
    message: str
