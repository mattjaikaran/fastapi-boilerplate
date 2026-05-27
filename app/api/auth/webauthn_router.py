"""WebAuthn / passkey endpoints.

Registration flow
-----------------
1. ``POST /auth/webauthn/register/begin``  (authenticated) → challenge JSON
2. Browser calls ``navigator.credentials.create(options)``
3. ``POST /auth/webauthn/register/complete`` (authenticated) → 201 credential

Authentication flow
-------------------
1. ``POST /auth/webauthn/authenticate/begin``  → challenge JSON
2. Browser calls ``navigator.credentials.get(options)``
3. ``POST /auth/webauthn/authenticate/complete`` → tokens
"""

from fastapi import APIRouter

from app.api.auth.dependencies import CurrentUser
from app.api.auth.schemas import (
    AuthResponse,
    MessageResponse,
    WebAuthnBeginAuthRequest,
    WebAuthnBeginRegistrationRequest,
    WebAuthnCompleteAuthRequest,
    WebAuthnCompleteRegistrationRequest,
    WebAuthnCredentialResponse,
)
from app.api.auth.webauthn_service import WebAuthnService
from app.api.users.service import UserService
from app.config.database import DBSession
from app.core.exceptions.auth import InvalidCredentialsError
from app.services.cache import CacheService

router = APIRouter(prefix="/webauthn", tags=["webauthn"])


def _svc(db: DBSession) -> WebAuthnService:
    return WebAuthnService(db=db, cache=CacheService())


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------


@router.post("/register/begin", response_model=dict)
async def begin_registration(
    body: WebAuthnBeginRegistrationRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """Return PublicKeyCredentialCreationOptions for the browser."""
    return await _svc(db).begin_registration(current_user)


@router.post("/register/complete", response_model=WebAuthnCredentialResponse, status_code=201)
async def complete_registration(
    body: WebAuthnCompleteRegistrationRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> WebAuthnCredentialResponse:
    """Verify the authenticator response and store the new credential."""
    credential = await _svc(db).complete_registration(
        current_user,
        credential_json=body.credential,
        device_name=body.device_name,
    )
    return WebAuthnCredentialResponse(
        id=str(credential.id),
        device_name=credential.device_name,
        created_at=credential.created_at.isoformat(),
        last_used_at=credential.last_used_at.isoformat() if credential.last_used_at else None,
        backup_eligible=credential.backup_eligible,
    )


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------


@router.post("/authenticate/begin", response_model=dict)
async def begin_authentication(body: WebAuthnBeginAuthRequest, db: DBSession) -> dict:
    """Return PublicKeyCredentialRequestOptions for the browser."""
    user = await UserService(db).get_by_email(body.email)
    if not user:
        raise InvalidCredentialsError()
    return await _svc(db).begin_authentication(user)


@router.post("/authenticate/complete", response_model=AuthResponse)
async def complete_authentication(
    body: WebAuthnCompleteAuthRequest, db: DBSession
) -> AuthResponse:
    """Verify the assertion and return JWT tokens."""
    user = await UserService(db).get_by_email(body.email)
    if not user:
        raise InvalidCredentialsError()
    return await _svc(db).complete_authentication(user, credential_json=body.credential)


# ------------------------------------------------------------------
# Credential management
# ------------------------------------------------------------------


@router.delete("/credentials/{credential_id}", response_model=MessageResponse)
async def delete_credential(
    credential_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Revoke / remove a registered passkey."""
    import uuid

    from sqlalchemy import select

    from app.api.auth.webauthn_model import WebAuthnCredential

    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == uuid.UUID(credential_id),
            WebAuthnCredential.user_id == current_user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise InvalidCredentialsError(detail="Credential not found")
    cred.is_active = False
    db.add(cred)
    return MessageResponse(message="Passkey removed successfully")
