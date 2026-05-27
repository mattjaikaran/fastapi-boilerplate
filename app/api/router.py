from fastapi import APIRouter  # noqa: I001

from app.api.api_keys.router import router as api_keys_router
from app.api.audit.router import router as audit_router
from app.api.auth.oauth import router as oauth_router
from app.api.auth.router import router as auth_router
from app.api.auth.webauthn_router import router as webauthn_router
from app.api.billing.router import router as billing_router
from app.api.feature_flags.router import router as feature_flags_router
from app.api.files.router import router as files_router
from app.api.health.router import router as health_router
from app.api.jobs.router import router as jobs_router
from app.api.notifications.router import router as notifications_router
from app.api.organizations.router import router as organizations_router
from app.api.search.router import router as search_router
from app.api.todos.router import router as todos_router
from app.api.users.router import router as users_router
from app.api.webhooks.router import router as webhooks_router
from app.api.ws.router import router as ws_router

# ai_router must be imported last — it triggers deferred model imports
from app.api.ai.router import router as ai_router  # noqa: I001

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(oauth_router)
api_router.include_router(webauthn_router)
api_router.include_router(users_router)
api_router.include_router(todos_router)
api_router.include_router(files_router)
api_router.include_router(organizations_router)
api_router.include_router(webhooks_router)
api_router.include_router(billing_router)
api_router.include_router(notifications_router)
api_router.include_router(audit_router)
api_router.include_router(feature_flags_router)
api_router.include_router(api_keys_router)
api_router.include_router(jobs_router)
api_router.include_router(search_router)
api_router.include_router(ws_router)
api_router.include_router(ai_router)
