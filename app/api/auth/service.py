import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.model import OTPCode, OTPPurpose, RefreshToken
from app.api.auth.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.api.users.model import User
from app.api.users.schemas import UserResponse
from app.api.users.service import UserService
from app.config.settings import settings
from app.core.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    InvalidOTPError,
    InvalidTokenError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.services.cache import CacheService


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


class AuthService:
    def __init__(self, db: AsyncSession, cache: CacheService) -> None:
        self.db = db
        self.cache = cache
        self.user_service = UserService(db)

    async def register(self, data: RegisterRequest) -> AuthResponse:
        from app.api.users.schemas import UserCreate

        user = await self.user_service.create(
            UserCreate(
                email=data.email,
                password=data.password,
                first_name=data.first_name,
                last_name=data.last_name,
            )
        )

        # Send verification email async
        await self._send_verification_otp(user)

        await self._notify(user.id, title="Welcome!", body="Your account has been created. Please verify your email.", type="success")

        tokens = await self._create_tokens(user)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    async def login(
        self,
        data: LoginRequest,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResponse:
        user = await self.user_service.get_by_email(data.email)
        if not user or not user.hashed_password:
            raise InvalidCredentialsError()

        await self._check_lockout(user.id)

        if not verify_password(data.password, user.hashed_password):
            await self._record_failed_attempt(user.id)
            raise InvalidCredentialsError()

        await self._clear_lockout(user.id)

        user.last_login_at = datetime.now(UTC)
        self.db.add(user)

        location = f" from {ip_address}" if ip_address else ""
        await self._notify(user.id, title="New login", body=f"Your account was accessed{location}.", type="info")

        tokens = await self._create_tokens(user, user_agent=user_agent, ip_address=ip_address)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        token_hash = _hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked.is_(False),
            )
        )
        stored = result.scalar_one_or_none()

        if not stored or stored.is_expired:
            raise InvalidTokenError(detail="Refresh token is invalid or expired")

        # Rotate refresh token
        stored.is_revoked = True
        self.db.add(stored)

        user = await self.user_service.get_by_id(stored.user_id)
        return await self._create_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        token_hash = _hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored:
            stored.is_revoked = True
            self.db.add(stored)

    async def request_otp(self, email: str, purpose: OTPPurpose) -> None:
        user = await self.user_service.get_by_email(email)
        if not user:
            return  # Don't leak whether email exists

        # Invalidate previous OTPs for same purpose
        old_otps = await self.db.execute(
            select(OTPCode).where(
                OTPCode.user_id == user.id,
                OTPCode.purpose == purpose,
                OTPCode.is_used.is_(False),
            )
        )
        for otp in old_otps.scalars().all():
            otp.is_used = True
            self.db.add(otp)

        code = _generate_otp(settings.OTP_LENGTH)
        otp = OTPCode(
            user_id=user.id,
            code=code,
            purpose=purpose,
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        self.db.add(otp)
        await self.db.flush()

        # Queue email task
        from app.workers.tasks.email import send_otp_email

        send_otp_email.delay(
            to_email=user.email,
            code=code,
            purpose=purpose.value,
            expires_minutes=settings.OTP_EXPIRE_MINUTES,
        )

    async def verify_otp(self, email: str, code: str, purpose: OTPPurpose) -> User:
        user = await self.user_service.get_by_email(email)
        if not user:
            raise InvalidOTPError()

        result = await self.db.execute(
            select(OTPCode).where(
                OTPCode.user_id == user.id,
                OTPCode.purpose == purpose,
                OTPCode.is_used.is_(False),
            ).order_by(OTPCode.created_at.desc())
        )
        otp = result.scalar_one_or_none()

        if not otp or not otp.is_valid:
            raise InvalidOTPError()

        otp.attempts += 1
        if otp.code != code:
            self.db.add(otp)
            raise InvalidOTPError()

        otp.is_used = True
        self.db.add(otp)

        if purpose == OTPPurpose.email_verification:
            user.is_email_verified = True
            self.db.add(user)

        return user

    async def forgot_password(self, email: str) -> None:
        await self.request_otp(email, OTPPurpose.password_reset)

    async def request_magic_link(self, email: str) -> None:
        """Send a magic link (OTP-backed token) to the user's email."""
        user = await self.user_service.get_by_email(email)
        if not user:
            return  # Don't leak whether email exists
        await self.request_otp(email, OTPPurpose.magic_link)

    async def verify_magic_link(self, token: str) -> AuthResponse:
        """Verify a magic link token and return a full auth response."""
        parts = token.split(":", 1)
        if len(parts) != 2:
            raise InvalidTokenError(detail="Invalid magic link token")
        email, code = parts
        user = await self.verify_otp(email, code, OTPPurpose.magic_link)
        if not user.is_email_verified:
            user.is_email_verified = True
            self.db.add(user)
        tokens = await self._create_tokens(user)
        from app.api.users.schemas import UserResponse
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    async def reset_password(self, email: str, code: str, new_password: str) -> None:
        user = await self.verify_otp(email, code, OTPPurpose.password_reset)
        user.hashed_password = get_password_hash(new_password)
        self.db.add(user)
        # Revoke all refresh tokens
        tokens = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.is_revoked.is_(False)
            )
        )
        for token in tokens.scalars().all():
            token.is_revoked = True
            self.db.add(token)
        await self._notify(user.id, title="Password changed", body="Your password was successfully reset.", type="warning")

    async def setup_totp(self, user: User) -> tuple[str, str]:
        secret = pyotp.random_base32()
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name=settings.APP_NAME
        )
        user.totp_secret = secret
        self.db.add(user)
        return secret, uri

    async def verify_totp(self, user: User, code: str) -> bool:
        if not user.totp_secret:
            return False
        totp = pyotp.TOTP(user.totp_secret)
        valid = totp.verify(code, valid_window=1)
        if valid and not user.is_totp_enabled:
            user.is_totp_enabled = True
            self.db.add(user)
        return valid

    async def _create_tokens(
        self,
        user: User,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        access_token = create_access_token(
            subject=str(user.id),
            extra={"role": user.role.value, "email": user.email},
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        token_hash = _hash_token(refresh_token)

        stored = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(stored)
        await self.db.flush()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def _send_verification_otp(self, user: User) -> None:
        await self.request_otp(user.email, OTPPurpose.email_verification)

    async def _check_lockout(self, user_id: uuid.UUID) -> None:
        key = f"lockout:{user_id}"
        locked = await self.cache.get(key)
        if locked:
            raise AccountLockedError()

    async def _record_failed_attempt(self, user_id: uuid.UUID) -> None:
        key = f"failed_attempts:{user_id}"
        attempts = await self.cache.increment(key, expire=300)
        if attempts >= 5:
            await self.cache.set(f"lockout:{user_id}", "1", expire=900)  # 15 min lockout

    async def _clear_lockout(self, user_id: uuid.UUID) -> None:
        await self.cache.delete(f"failed_attempts:{user_id}")
        await self.cache.delete(f"lockout:{user_id}")

    async def _notify(self, user_id: uuid.UUID, title: str, body: str | None = None, type: str = "info") -> None:
        from app.api.notifications.model import NotificationType
        from app.api.notifications.service import NotificationService

        try:
            notification_type = NotificationType(type)
            await NotificationService(self.db).create(user_id=user_id, title=title, body=body, type=notification_type)
        except Exception:
            pass  # Notifications are non-critical; never block auth flows
