"""WebAuthn / passkey registration and authentication service."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import webauthn
from sqlalchemy import select
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.api.auth.schemas import AuthResponse, TokenResponse
from app.api.auth.webauthn_model import WebAuthnCredential
from app.api.users.model import User
from app.api.users.schemas import UserResponse
from app.config.settings import settings
from app.core.exceptions.auth import InvalidCredentialsError, InvalidTokenError
from app.core.security import create_access_token, create_refresh_token

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.services.cache import CacheService

_CHALLENGE_TTL = 300  # 5 minutes


def _challenge_key(kind: str, user_id: str) -> str:
    return f"webauthn:{kind}:challenge:{user_id}"


class WebAuthnService:
    def __init__(self, db: AsyncSession, cache: CacheService) -> None:
        self.db = db
        self.cache = cache

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def begin_registration(self, user: User) -> dict:
        """Generate registration options and cache the challenge."""
        existing: list[WebAuthnCredential] = await self._credentials_for(user)
        exclude = [
            PublicKeyCredentialDescriptor(id=c.credential_id)
            for c in existing
        ]

        options = webauthn.generate_registration_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            user_id=str(user.id).encode(),
            user_name=user.email,
            user_display_name=user.full_name,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
            exclude_credentials=exclude,
        )

        # Persist challenge so /complete can verify it
        challenge_b64 = webauthn.base64url_to_bytes(
            webauthn.options_to_json(options)
        )
        # options_to_json returns JSON string; parse to get raw challenge
        options_dict = json.loads(webauthn.options_to_json(options))
        await self.cache.set(
            _challenge_key("register", str(user.id)),
            options_dict["challenge"],
            expire=_CHALLENGE_TTL,
        )

        return options_dict

    async def complete_registration(
        self,
        user: User,
        credential_json: str | dict,
        device_name: str | None = None,
    ) -> WebAuthnCredential:
        """Verify authenticator response and persist the new credential."""
        challenge_b64: str | None = await self.cache.get(
            _challenge_key("register", str(user.id))
        )
        if not challenge_b64:
            raise InvalidTokenError(detail="Registration challenge expired or not found")

        verification = webauthn.verify_registration_response(
            credential=credential_json,
            expected_challenge=webauthn.base64url_to_bytes(challenge_b64),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=False,
        )

        credential = WebAuthnCredential(
            user_id=user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            aaguid=str(verification.aaguid) if verification.aaguid else "",
            device_name=device_name,
            backup_eligible=verification.credential_backed_up,
            backup_state=verification.credential_backed_up,
            transports=json.dumps(
                [t.value for t in verification.credential_device_type.__class__]
            ) if hasattr(verification, "credential_device_type") else None,
        )
        self.db.add(credential)

        await self.cache.delete(_challenge_key("register", str(user.id)))

        return credential

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def begin_authentication(self, user: User) -> dict:
        """Generate authentication options and cache the challenge."""
        existing = await self._credentials_for(user)
        if not existing:
            raise InvalidCredentialsError(detail="No passkeys registered for this account")

        allow = [
            PublicKeyCredentialDescriptor(id=c.credential_id)
            for c in existing
        ]

        options = webauthn.generate_authentication_options(
            rp_id=settings.WEBAUTHN_RP_ID,
            allow_credentials=allow,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        options_dict = json.loads(webauthn.options_to_json(options))
        await self.cache.set(
            _challenge_key("auth", str(user.id)),
            options_dict["challenge"],
            expire=_CHALLENGE_TTL,
        )

        return options_dict

    async def complete_authentication(
        self,
        user: User,
        credential_json: str | dict,
    ) -> AuthResponse:
        """Verify assertion and return JWT tokens."""
        challenge_b64: str | None = await self.cache.get(
            _challenge_key("auth", str(user.id))
        )
        if not challenge_b64:
            raise InvalidTokenError(detail="Authentication challenge expired or not found")

        # Look up stored credential by raw credential_id from response
        raw_id_b64 = (
            credential_json.get("rawId") or credential_json.get("id")
            if isinstance(credential_json, dict)
            else None
        )
        if not raw_id_b64:
            raise InvalidCredentialsError(detail="Missing credential id in response")

        raw_id_bytes = webauthn.base64url_to_bytes(raw_id_b64)
        stored = await self._credential_by_id(raw_id_bytes)
        if not stored or stored.user_id != user.id:
            raise InvalidCredentialsError(detail="Credential not found")

        verification = webauthn.verify_authentication_response(
            credential=credential_json,
            expected_challenge=webauthn.base64url_to_bytes(challenge_b64),
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=False,
        )

        # Update sign count + last used
        stored.sign_count = verification.new_sign_count
        stored.last_used_at = datetime.now(UTC)
        self.db.add(stored)

        await self.cache.delete(_challenge_key("auth", str(user.id)))

        tokens = await self._create_tokens(user)
        return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _credentials_for(self, user: User) -> list[WebAuthnCredential]:
        result = await self.db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.user_id == user.id,
                WebAuthnCredential.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def _credential_by_id(self, credential_id: bytes) -> WebAuthnCredential | None:
        result = await self.db.execute(
            select(WebAuthnCredential).where(
                WebAuthnCredential.credential_id == credential_id
            )
        )
        return result.scalar_one_or_none()

    async def _create_tokens(self, user: User) -> TokenResponse:
        import hashlib

        from app.api.auth.model import RefreshToken

        access_token = create_access_token(
            subject=str(user.id),
            extra={"role": user.role.value, "email": user.email},
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        from datetime import timedelta

        stored = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(stored)
        await self.db.flush()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
