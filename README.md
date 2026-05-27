# FastAPI Boilerplate

Production-ready FastAPI + PostgreSQL boilerplate. Async SQLAlchemy, Alembic, Redis, Celery, Stripe, OAuth2, full auth system, audit logging, feature flags, WebSocket-ready, and comprehensive tests — wired up and ready to ship.

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **FastAPI** + Uvicorn | ASGI, async-first, auto OpenAPI docs |
| ORM | **SQLAlchemy 2** (async) + Alembic | Type-safe, async, full migration history |
| Database | **PostgreSQL** via asyncpg | Async driver, production-grade |
| Cache | **Redis** (asyncio) | Distributed cache, lockout, session data |
| Task Queue | **Celery** + Redis | Background jobs, email, cron |
| Auth | JWT + argon2/bcrypt + TOTP + OAuth2 | Every modern auth pattern covered |
| Payments | **Stripe** | Checkout, portal, webhooks |
| Email | **Resend** | Transactional email with queue |
| Storage | **Local / S3** | Configurable via `STORAGE_DRIVER` |
| Observability | **OpenTelemetry** + Sentry + Prometheus | Traces, errors, metrics |
| Logging | **structlog** | Structured JSON logs in production |
| Admin | **SQLAdmin** | Auto-generated admin panel at `/admin` |
| Package manager | **uv** | Fast installs, lockfile |

## Feature Overview

| Feature | Status |
|---|---|
| Email/password auth | ✓ |
| JWT access + refresh tokens (rotation) | ✓ |
| OTP codes (email verification, password reset, 2FA) | ✓ |
| Magic link (passwordless) | ✓ |
| TOTP (authenticator app 2FA) | ✓ |
| Google + GitHub OAuth2 | ✓ |
| Account lockout (brute-force protection) | ✓ |
| API key authentication | ✓ |
| RBAC (user / admin / superuser roles) | ✓ |
| Rate limiting (per-endpoint) | ✓ |
| Organizations + multi-tenancy | ✓ |
| Feature flags (boolean, percentage, A/B) | ✓ |
| Audit logging | ✓ |
| File uploads (local + S3) | ✓ |
| Background email queue | ✓ |
| Celery workers + beat scheduler | ✓ |
| Stripe checkout + portal + webhooks | ✓ |
| Notifications system | ✓ |
| Webhook event delivery | ✓ |
| Full-text search | ✓ |
| AI/ML task queue | ✓ |
| Prometheus metrics endpoint | ✓ |
| OpenTelemetry distributed tracing | ✓ |
| Sentry error tracking | ✓ |
| GZip response compression | ✓ |
| Security headers | ✓ |
| Graceful shutdown | ✓ |
| SQLAdmin panel | ✓ |
| Health check endpoints | ✓ |
| Swagger UI (dev only) | ✓ |

## Quick Start

```bash
# 1. Clone and install
git clone <repo> fastapi-boilerplate && cd fastapi-boilerplate
make setup          # uv sync + copy .env.example → .env

# 2. Start infrastructure
make up             # postgres + redis

# 3. Initialize database
make migrate        # run Alembic migrations
make seed           # seed admin + sample data

# 4. Start dev server
make dev

# API:   http://localhost:8000/api/
# Docs:  http://localhost:8000/docs
# Admin: http://localhost:8000/admin
```

Or run the quickstart (clone-to-running in one command):

```bash
make quickstart
```

## Project Structure

```
app/
├── main.py                  # FastAPI factory — middleware, routers, events, OTel
├── config/
│   ├── settings.py          # Pydantic Settings (env-driven, validated)
│   └── database.py          # Async SQLAlchemy engine + session factory
├── models/
│   └── base.py              # Base, TimestampMixin, SoftDeleteMixin, UUIDMixin
├── core/
│   ├── dependencies/        # Shared FastAPI dependencies
│   ├── exceptions/          # AppError hierarchy + exception handlers
│   ├── middleware/          # RequestID, Logging, GZip, SecurityHeaders
│   ├── pagination/          # Pagination schema + helpers
│   ├── rate_limit.py        # slowapi limiter
│   └── security/            # JWT (create/decode), password hash/verify
├── services/
│   ├── base.py              # Abstract CRUDService[M, C, U]
│   ├── cache.py             # Redis CacheService
│   ├── email.py             # Resend EmailService
│   └── storage.py           # Local/S3 StorageService
├── api/
│   ├── router.py            # Top-level APIRouter aggregating all modules
│   ├── auth/                # register, login, logout, refresh, OTP, TOTP, magic link
│   ├── users/               # profile, admin CRUD, API key management
│   ├── todos/               # CRUD, stats, search, bulk ops
│   ├── organizations/       # CRUD + membership management
│   ├── billing/             # Stripe checkout, portal, webhook handler
│   ├── notifications/       # Create, list, mark read
│   ├── audit/               # Read-only audit log
│   ├── feature_flags/       # Boolean, percentage, A/B flags
│   ├── api_keys/            # Key generation + validation
│   ├── files/               # Multipart upload, serve, delete
│   ├── jobs/                # Background job tracking
│   ├── webhooks/            # Outbound webhook delivery
│   ├── search/              # Full-text cross-entity search
│   ├── health/              # /live, /ready, /info
│   └── ai/                  # AI/ML task endpoints
├── admin/                   # SQLAdmin views + authentication
└── workers/
    ├── celery_app.py        # Celery app + beat schedule
    └── tasks/
        ├── email.py         # Async email sending
        ├── notifications.py # Async notification delivery
        ├── maintenance.py   # Token cleanup, audit purge
        └── ml.py            # AI/ML tasks
migrations/
├── versions/                # Alembic migration files
└── env.py                   # Alembic env config
tests/
├── conftest.py              # Fixtures: db, client, user, admin, auth_headers
├── factories/               # factory_boy factories for all models
├── unit/                    # Fast isolated unit tests
├── integration/             # Tests that hit real DB (NullPool)
└── e2e/                     # End-to-end user journey tests
scripts/
├── seed_data.py             # Dev data: admin + users + todos + orgs
├── create_superuser.py      # Create initial superuser
├── setup.sh                 # Env setup helper
└── doctor.sh                # Dev environment validator
```

## API Endpoints

### Auth `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /register | — | Register with email + password |
| POST | /login | — | Login; returns token pair |
| POST | /refresh | — | Rotate token pair |
| POST | /logout | — | Revoke refresh token |
| GET | /me | JWT | Current user profile |
| POST | /forgot-password | — | Send password reset OTP |
| POST | /reset-password | — | Reset password with OTP |
| POST | /change-password | JWT | Change password |
| POST | /request-otp | — | Request OTP (any purpose) |
| POST | /verify-otp | — | Verify OTP code |
| POST | /magic-link/request | — | Send magic link email |
| POST | /magic-link/verify | — | Authenticate via magic link token |
| GET | /google | — | Google OAuth redirect |
| GET | /google/callback | — | Google OAuth callback |
| GET | /github | — | GitHub OAuth redirect |
| GET | /github/callback | — | GitHub OAuth callback |
| POST | /totp/setup | JWT | Generate TOTP secret + QR code |
| POST | /totp/verify | JWT | Enable TOTP after verifying first code |

### Users `/api/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /me | JWT | Get own profile |
| PATCH | /me | JWT | Update own profile |
| DELETE | /me | JWT | Soft-delete own account |
| POST | /me/api-keys | JWT | Create API key |
| GET | /me/api-keys | JWT | List own API keys |
| DELETE | /me/api-keys/:id | JWT | Revoke API key |
| GET | / | Admin | List all users |
| GET | /:id | Admin | Get user by ID |
| PATCH | /:id | Admin | Update user |
| DELETE | /:id | Admin | Soft-delete user |

### Todos `/api/todos`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | / | JWT | List with filtering and pagination |
| POST | / | JWT | Create todo |
| GET | /stats | JWT | Aggregated stats (total, completed, overdue, by priority) |
| GET | /:id | JWT | Get by ID |
| PATCH | /:id | JWT | Update |
| DELETE | /:id | JWT | Soft delete |
| POST | /:id/toggle | JWT | Toggle completion status |
| PATCH | /bulk | JWT | Bulk update by IDs |
| POST | /bulk-delete | JWT | Bulk delete by IDs |

Query params for `GET /`: `search`, `priority` (low/medium/high), `completed` (bool), `overdue` (bool), `due_today` (bool), `page`, `limit`.

### Organizations `/api/organizations`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | / | JWT | Create organization |
| GET | / | JWT | List own organizations |
| GET | /:id | Member | Get organization |
| PATCH | /:id | Admin | Update organization |
| DELETE | /:id | Owner | Delete organization |
| GET | /:id/members | Member | List members |
| POST | /:id/members | Admin | Add member |
| DELETE | /:id/members/:uid | Admin | Remove member |

### Billing `/api/billing`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /checkout | JWT | Create Stripe checkout session |
| POST | /portal | JWT | Create billing portal session |
| POST | /webhook | — | Stripe webhook handler |
| GET | /subscription | JWT | Get active subscription |
| DELETE | /subscription | JWT | Cancel subscription |

### Files `/api/files`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /upload | JWT | Upload file (multipart/form-data) |
| GET | /:id | JWT | Get file metadata |
| DELETE | /:id | JWT | Delete file |

### System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /api/health/live | — | Liveness probe |
| GET | /api/health/ready | — | Readiness probe (DB + Redis) |
| GET | /api/health/info | — | App version + env |
| GET | /metrics | — | Prometheus metrics |

## Environment Variables

See `.env.example` for the full list. Key variables:

```bash
# App
APP_ENV=development
SECRET_KEY=<min 32 chars>
APP_NAME="My API"

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db

# JWT
JWT_SECRET_KEY=<min 32 chars>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (Resend)
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com

# OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Stripe
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Observability
SENTRY_DSN=https://...
OTEL_ENABLED=false
PROMETHEUS_ENABLED=true
```

## Development

```bash
make dev          # hot reload (uvicorn --reload)
make lint         # ruff check
make lint-fix     # ruff check --fix
make format       # ruff format
make typecheck    # mypy
make test         # pytest (all)
make test-unit    # unit tests only
make test-integration  # integration tests (needs DB)
make test-cov     # with HTML coverage report
```

## Database

```bash
make migrate          # apply pending migrations
make migration msg="add foo table"  # generate new migration
make migrate-down     # rollback one
make seed             # load dev seed data
make db-reset         # drop + recreate + migrate (dev only)
```

Seed credentials (all use `password123`):

- `admin@example.com` (superuser)
- `alice@example.com`, `bob@example.com`, `charlie@example.com`

### Migrations

Migration files live in `migrations/versions/`. **Never use schema sync in production** — always generate + apply migration files.

```bash
# Dev workflow
make migration msg="add subscription_tiers table"
make migrate

# Production (run before new binary starts)
uv run alembic upgrade head
```

## Authentication

### JWT Flow

1. `POST /api/auth/login` → `{ tokens: { access_token, refresh_token }, user }`
2. Use `Authorization: Bearer <access_token>` on protected endpoints
3. When access token expires, call `POST /api/auth/refresh` with `{ refresh_token }`
4. Refresh tokens are single-use (rotated on each refresh)

### OTP Flow

```bash
# Request code
POST /api/auth/request-otp
{ "email": "user@example.com", "purpose": "email_verification" }

# Verify code
POST /api/auth/verify-otp
{ "email": "user@example.com", "code": "123456", "purpose": "email_verification" }
```

Purposes: `email_verification`, `password_reset`, `two_factor`, `magic_link`

### Magic Link

```bash
# Request link
POST /api/auth/magic-link/request
{ "email": "user@example.com" }

# Authenticate
POST /api/auth/magic-link/verify
{ "token": "<token-from-email>" }
```

### API Keys

```bash
# Create key
POST /api/users/me/api-keys
{ "name": "CI/CD key" }

# Use key
GET /api/auth/me
X-Api-Key: <key>
```

## Docker

```bash
make up                           # postgres + redis + api
make up-celery                    # + Celery worker
make up-monitoring                # + Celery worker + Flower
make down
make logs
```

## Production Build

```bash
docker build -t my-api .
docker run -p 8000:8000 --env-file .env my-api
```

In `production` mode:
- Swagger/ReDoc/OpenAPI JSON disabled
- Structured JSON logging enabled
- `APP_DEBUG=false`

## Testing

```bash
make test               # all tests
make test-unit          # unit tests (fast, isolated)
make test-integration   # integration tests (needs postgres + redis)
make test-e2e           # E2E user journey tests
make test-cov           # with HTML coverage report at htmlcov/index.html
```

Tests use real database (NullPool) — no mocking the ORM. Factories via `factory_boy`.

## Performance Notes

- **asyncpg** over psycopg2: async I/O, no blocking thread pool
- **orjson** default response class: ~2x faster JSON serialization
- **GZip** middleware: ~70% size reduction on JSON responses
- **structlog** JSON renderer in production: machine-parseable logs
- **Redis** for cache + lockout + OTP: avoids extra DB round-trips
- Connection pool: `DATABASE_POOL_SIZE=20`, `DATABASE_MAX_OVERFLOW=40`

## Security Checklist

- [x] `SECRET_KEY` min 32 chars, validated on production
- [x] `JWT_SECRET_KEY` separate from `SECRET_KEY`
- [x] Passwords hashed with bcrypt
- [x] Refresh tokens hashed before storage (SHA-256)
- [x] Account lockout after 5 failed attempts (15 min)
- [x] Rate limiting on auth endpoints
- [x] CORS configured via `CORS_ORIGINS`
- [x] Security headers on all responses
- [x] API keys hashed before storage
- [x] SQL injection prevented via SQLAlchemy parameterized queries
- [x] File upload size capped via `UPLOAD_MAX_SIZE_MB`
- [x] Stripe webhook signature verified
