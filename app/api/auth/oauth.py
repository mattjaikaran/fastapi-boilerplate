import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from app.api.auth.service import AuthService
from app.api.users.model import User
from app.config.database import DBSession
from app.config.settings import settings
from app.core.security import create_access_token, create_refresh_token
from app.services.cache import CacheService

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])

_SUPPORTED_PROVIDERS = {"google", "github"}

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def _callback_uri(provider: str) -> str:
    return f"{settings.OAUTH_REDIRECT_FRONTEND_URL.rstrip('/')}/../../api/auth/oauth/{provider}/callback"


def _get_redirect_uri(request: Request, provider: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/auth/oauth/{provider}/callback"


@router.get("/{provider}")
async def oauth_login(provider: str, request: Request) -> RedirectResponse:
    if provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"OAuth provider '{provider}' not supported")

    redirect_uri = _get_redirect_uri(request, provider)
    import secrets as _secrets

    state = _secrets.token_urlsafe(32)
    cache = CacheService()
    await cache.set(f"oauth_state:{state}", provider, expire=600)

    if provider == "google":
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=501, detail="Google OAuth not configured")
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
        }
        auth_url = _GOOGLE_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())

    elif provider == "github":
        if not settings.GITHUB_CLIENT_ID:
            raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        auth_url = _GITHUB_AUTH_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())

    return RedirectResponse(url=auth_url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    db: DBSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    if provider not in _SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"OAuth provider '{provider}' not supported")

    if error:
        return RedirectResponse(
            url=f"{settings.OAUTH_REDIRECT_FRONTEND_URL}?error={error}"
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")

    cache = CacheService()
    stored_provider = await cache.get(f"oauth_state:{state}")
    if stored_provider != provider:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    await cache.delete(f"oauth_state:{state}")

    redirect_uri = _get_redirect_uri(request, provider)

    if provider == "google":
        email, name, provider_id = await _exchange_google(code, redirect_uri)
    else:
        email, name, provider_id = await _exchange_github(code, redirect_uri)

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from provider")

    user = await _find_or_create_oauth_user(
        db=db,
        email=email,
        name=name,
        provider=provider,
        provider_id=provider_id,
    )

    access_token = create_access_token(
        subject=str(user.id),
        extra={"role": user.role.value, "email": user.email},
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    auth_service = AuthService(db=db, cache=CacheService())
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None
    await auth_service._create_tokens(user, user_agent=user_agent, ip_address=ip_address)

    return RedirectResponse(
        url=f"{settings.OAUTH_REDIRECT_FRONTEND_URL}?access_token={access_token}&refresh_token={refresh_token}"
    )


async def _exchange_google(code: str, redirect_uri: str) -> tuple[str, str, str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

        info_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        info_resp.raise_for_status()
        info = info_resp.json()

    email = info.get("email", "")
    name = info.get("name", "") or info.get("given_name", "")
    provider_id = info.get("sub", "")
    return email, name, provider_id


async def _exchange_github(code: str, redirect_uri: str) -> tuple[str, str, str]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _GITHUB_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        token_data = resp.json()
        access_token = token_data["access_token"]
        auth_header = {"Authorization": f"Bearer {access_token}"}

        user_resp = await client.get(_GITHUB_USER_URL, headers=auth_header)
        user_resp.raise_for_status()
        user_info = user_resp.json()

        email = user_info.get("email")
        if not email:
            emails_resp = await client.get(_GITHUB_EMAILS_URL, headers=auth_header)
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None
            )
            email = primary["email"] if primary else ""

    name = user_info.get("name") or user_info.get("login", "")
    provider_id = str(user_info["id"])
    return email, name, provider_id


async def _find_or_create_oauth_user(
    db: DBSession,
    email: str,
    name: str,
    provider: str,
    provider_id: str,
) -> User:
    from sqlalchemy import select

    from app.api.users.model import User as UserModel

    result = await db.execute(
        select(UserModel).where(UserModel.email == email)
    )
    user = result.scalar_one_or_none()

    if user:
        if not user.oauth_provider:
            user.oauth_provider = provider
            user.oauth_provider_id = provider_id
            db.add(user)
        return user

    first_name, _, last_name = name.partition(" ")
    user = UserModel(
        email=email,
        first_name=first_name or None,
        last_name=last_name or None,
        is_email_verified=True,
        oauth_provider=provider,
        oauth_provider_id=provider_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
