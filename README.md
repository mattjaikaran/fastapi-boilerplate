# FastAPI Boilerplate

Production-ready FastAPI + PostgreSQL backend. Async-first, batteries included — auth, billing, background jobs, observability, and a full test suite ready to ship.

[![Version 0.1.0](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![SQLAlchemy 2](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg)](https://docs.sqlalchemy.org/)
[![uv](https://img.shields.io/badge/uv-package--manager-blueviolet)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/badge/linting-ruff-orange)](https://github.com/astral-sh/ruff)

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The current version is **0.1.0**. The version in `pyproject.toml` is the single source of truth: the app reads it at run time (`/api/health/info`) unless you set `APP_VERSION`. Run `make version` to print it. While the major version is 0, minor releases can include breaking changes.

See [CHANGELOG.md](CHANGELOG.md) for release notes and [docs/RELEASING.md](docs/RELEASING.md) for the release process.

---

## Architecture

```mermaid
graph LR
    CLIENT[Client] --> APP[FastAPI app]
    APP --> PG[(PostgreSQL)]
    APP --> REDIS[(Redis)]
    APP --> WORKERS[Celery workers]
    APP --> EXTERNAL[External services]
    APP --> OBS[Observability]
    WORKERS --> REDIS
    WORKERS --> PG
```

### Request Path

```mermaid
graph LR
    CLIENT[Client] --> MW["Middleware<br/>CORS · rate limit · auth"]
    MW --> ROUTER[API router]
    ROUTER --> SERVICE[Service layer]
    SERVICE --> MODEL[SQLAlchemy models]
    MODEL --> PG[(PostgreSQL)]
```

### Background Work

```mermaid
graph LR
    APP[FastAPI app] -->|enqueue| REDIS[(Redis)]
    BEAT[Celery beat] -->|schedule| REDIS
    REDIS --> EMAIL[email]
    REDIS --> NOTIF[notifications]
    REDIS --> ML[ml]
    REDIS --> WEBHOOKS[webhooks]
    EMAIL --> WORKER[Celery worker]
    NOTIF --> WORKER
    ML --> WORKER
    WEBHOOKS --> WORKER
```

### External Services

```mermaid
graph LR
    APP[FastAPI app] --> STRIPE[Stripe]
    APP --> RESEND[Resend]
    APP --> S3[(S3)]
    APP --> OTEL[OpenTelemetry]
    APP --> SENTRY[Sentry]
    APP --> LOGS[structlog]
    PROM[Prometheus] -->|scrape| APP
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | **FastAPI** + Uvicorn (ASGI) |
| ORM | **SQLAlchemy 2** async + Alembic |
| Database | **PostgreSQL 17** via asyncpg |
| Cache / Queue | **Redis 7** (asyncio) |
| Task Queue | **Celery** + Redis broker |
| Auth | JWT via **PyJWT** + passwords via **bcrypt** + TOTP + OAuth2 + WebAuthn |
| Payments | **Stripe** (checkout, portal, webhooks) |
| Email | **Resend** |
| File Storage | **Local / S3** (configurable) |
| AI | Anthropic + OpenAI clients |
| Observability | OpenTelemetry + Sentry + Prometheus |
| Logging | **structlog** (JSON in production) |
| Admin | **SQLAdmin** at `/admin` |
| Package Manager | **uv** |
| Optional services | pgvector, RabbitMQ, Neo4j, SeaweedFS — see [docs/SERVICES.md](docs/SERVICES.md) |
| Linting | **Ruff** (strict rule set, see `pyproject.toml`) |
| Type Checking | **mypy** with the pydantic plugin |

---

## Features

| Category | Feature |
|---|---|
| **Auth** | Email/password, JWT access + refresh (rotation), OTP, magic link, TOTP (authenticator app) |
| **Auth** | Google + GitHub OAuth2, WebAuthn / passkeys, API key auth |
| **Auth** | Account lockout (brute-force), per-endpoint rate limiting |
| **Access Control** | RBAC — user / admin / superuser roles |
| **Multi-tenancy** | Organizations + member roles (owner / admin / member) |
| **Payments** | Stripe checkout, billing portal, webhook handler, subscription tracking |
| **Background Jobs** | Celery workers + beat scheduler, job tracking API |
| **Notifications** | In-app notifications + async delivery queue |
| **Webhooks** | Inbound webhook receiver with stored events and async processing |
| **Feature Flags** | Boolean, percentage rollout, A/B variants |
| **File Uploads** | Multipart upload, local or S3 storage |
| **Search** | Full-text cross-entity search |
| **Audit** | Append-only audit log on all mutations |
| **AI/ML** | Anthropic + OpenAI clients, ML task queue |
| **Observability** | OTel traces, Sentry errors, Prometheus metrics, structured logs |
| **Admin** | SQLAdmin panel — auto-generated CRUD for all models |
| **WebSockets** | Real-time push via ConnectionManager |
| **Security** | Security headers (HSTS, CSP), GZip, CORS, parameterized queries |
| **Developer Experience** | Hot reload, factory-boy test fixtures, real-DB integration tests |

---

## Quick start

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/), Docker with the Compose plugin, and `make`. Python 3.13 is installed by uv when your system Python is older.

```bash
# 1. Install
git clone <repo> && cd fastapi-boilerplate
./scripts/setup.sh  # uv sync + .env with generated SECRET_KEY and JWT_SECRET_KEY

# 2. Start infrastructure and the API (Docker)
make up             # postgres + redis + api on port 8100

# 3. Database
make migrate        # run Alembic migrations
make seed           # seed admin + sample data
```

`make setup` is a shorter alternative to `./scripts/setup.sh`. It copies `.env.example` to `.env` but does not generate secrets.

To run everything in one command, use `make quickstart` (setup, start, migrate, seed).

Run `./scripts/doctor.sh` to check your toolchain, `.env`, dependencies, and services.

| URL | Description |
|---|---|
| `http://localhost:8100/api/` | REST API |
| `http://localhost:8100/docs` | Swagger UI (dev only) |
| `http://localhost:8100/redoc` | ReDoc |
| `http://localhost:8100/admin` | SQLAdmin panel |
| `http://localhost:8100/metrics` | Prometheus metrics |

Default port is 8100 so the API runs beside Django on 8000.

To run the API on your machine instead of in Docker (`make dev`), see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Create an admin account with `make create-superuser EMAIL=you@example.com`.

### Optional services

pgvector, RabbitMQ, Neo4j, SeaweedFS, Celery workers, and Flower are off by default. Each has a Compose profile and a Make target (for example `make up-vector`, `make up-graph`, `make up-storage`). See [docs/SERVICES.md](docs/SERVICES.md) for ports, env vars, and details.

---

## Project Structure

```
app/
├── main.py                    # FastAPI factory — middleware, lifespan, OTel, Sentry
├── config/
│   ├── settings.py            # Pydantic Settings (env-driven, validated at boot)
│   └── database.py            # Async SQLAlchemy engine + session factory
├── models/
│   └── base.py                # BaseModel (UUID PK + timestamps), SoftDeleteMixin
├── core/
│   ├── dependencies/          # shared FastAPI dependencies
│   ├── exceptions/            # AppError hierarchy + exception handlers
│   ├── middleware/            # RequestID, Logging, SecurityHeaders, RateLimit, Envelope
│   ├── pagination/            # Page-based pagination schemas
│   ├── rate_limit.py          # slowapi limiter config
│   └── security/              # JWT (PyJWT) create/decode, password hash/verify (bcrypt)
├── services/
│   ├── base.py                # Generic CRUDService[Model, Create, Update]
│   ├── cache.py               # Redis CacheService
│   ├── email.py               # Resend EmailService
│   ├── storage.py             # Local/S3 StorageService
│   ├── ai/                    # Anthropic + OpenAI clients
│   ├── graph/                 # Neo4j client (optional graph extra)
│   ├── integrations/          # Django Ninja HTTP client
│   └── messaging/             # RabbitMQ publish/consume (optional mq extra)
├── agents/                    # Pydantic AI and LangGraph agents (optional agents extra)
├── api/
│   ├── router.py              # Top-level APIRouter — aggregates the module routers
│   ├── auth/                  # register, login, refresh, OTP, TOTP, magic link, OAuth, WebAuthn
│   ├── users/                 # profile CRUD, API key management
│   ├── organizations/         # orgs + membership
│   ├── todos/                 # CRUD, search, stats, bulk ops (reference module)
│   ├── billing/               # Stripe checkout, portal, webhooks
│   ├── notifications/         # in-app notifications
│   ├── audit/                 # read-only audit log
│   ├── feature_flags/         # boolean, percentage, A/B flags
│   ├── api_keys/              # API key CRUD
│   ├── files/                 # multipart upload, serve, delete
│   ├── jobs/                  # background job tracking
│   ├── webhooks/              # inbound webhook events
│   ├── search/                # full-text search
│   ├── health/                # /live, /ready, /info
│   ├── ai/                    # AI/ML endpoints
│   └── ws/                    # WebSocket endpoint + ConnectionManager
├── admin/                     # SQLAdmin views + auth
└── workers/
    ├── celery_app.py          # Celery app + beat schedule
    └── tasks/
        ├── email.py           # email delivery tasks
        ├── notifications.py   # notification delivery tasks
        ├── maintenance.py     # token cleanup, audit purge (scheduled)
        ├── ml.py              # AI/ML processing tasks
        └── webhooks.py        # inbound webhook event processing

migrations/versions/           # Alembic revisions: 0000_baseline … 0005_align_indexes_with_models
tests/
├── conftest.py                # fixtures: db, client, user, admin, auth_headers
├── factories/                 # factory_boy factories
├── unit/                      # fast, isolated
├── integration/               # real DB (NullPool), one per module
└── e2e/                       # full user journey tests
scripts/
├── seed_data.py               # dev data: admin + users + todos + orgs
├── create_superuser.py        # create or promote a superuser
├── generate_module.py         # scaffold a new API module (5-file pattern)
├── load_tests.py              # Locust load tests (make test-load)
├── setup.sh                   # bootstrap: uv sync + .env with generated secrets
└── doctor.sh                  # environment validator
docker/postgres/init/          # SQL scripts run on first Postgres start
docs/                          # guides and the exported openapi.json
.github/workflows/             # ci.yml, release.yml
.pre-commit-config.yaml        # pre-commit hooks
CHANGELOG.md                   # release notes
```

---

## API Reference

### Auth `/api/auth`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | — | Register with email + password |
| POST | `/login` | — | Returns access + refresh token pair |
| POST | `/refresh` | — | Rotate token pair (single-use refresh) |
| POST | `/logout` | JWT | Revoke refresh token |
| GET | `/me` | JWT | Current user profile |
| POST | `/forgot-password` | — | Send password reset OTP |
| POST | `/reset-password` | — | Reset with OTP code |
| POST | `/change-password` | JWT | Authenticated password change |
| POST | `/request-otp` | — | Request OTP (any purpose) |
| POST | `/verify-otp` | — | Verify OTP code |
| POST | `/magic-link/request` | — | Send magic link email |
| POST | `/magic-link/verify` | — | Authenticate via token |
| GET | `/oauth/{provider}` | — | OAuth2 redirect (`google` or `github`) |
| GET | `/oauth/{provider}/callback` | — | OAuth2 callback |
| POST | `/totp/setup` | JWT | Generate TOTP secret + QR code |
| POST | `/totp/verify` | JWT | Enable TOTP (verify first code) |

### WebAuthn `/api/webauthn`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register/begin` | JWT | Begin passkey registration |
| POST | `/register/complete` | JWT | Complete passkey registration |
| POST | `/authenticate/begin` | — | Begin passkey authentication |
| POST | `/authenticate/complete` | — | Complete passkey authentication |
| GET | `/credentials` | JWT | List registered passkeys |
| DELETE | `/credentials/{credential_id}` | JWT | Remove a passkey |

### Users `/api/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/me` | JWT | Get own profile |
| PATCH | `/me` | JWT | Update own profile |
| DELETE | `/me` | JWT | Soft-delete own account |
| POST | `/me/api-keys` | JWT | Create API key |
| GET | `/me/api-keys` | JWT | List own API keys |
| DELETE | `/me/api-keys/:id` | JWT | Revoke API key |
| GET | `/` | Admin | List all users (paginated) |
| GET | `/:id` | Admin | Get user by ID |
| PATCH | `/:id` | Admin | Update user |
| DELETE | `/:id` | Admin | Soft-delete user |

### Organizations `/api/organizations`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | JWT | Create organization |
| GET | `/` | JWT | List own organizations |
| GET | `/:id` | Member | Get organization |
| PATCH | `/:id` | Org Admin | Update organization |
| DELETE | `/:id` | Owner | Delete organization |
| GET | `/:id/members` | Member | List members |
| POST | `/:id/members` | Org Admin | Add member |
| DELETE | `/:id/members/:uid` | Org Admin | Remove member |

### Todos `/api/todos` (reference CRUD module)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | JWT | List with filters + pagination |
| POST | `/` | JWT | Create |
| GET | `/stats` | JWT | Aggregated stats (total, done, overdue, by priority) |
| GET | `/:id` | JWT | Get by ID |
| PATCH | `/:id` | JWT | Update |
| DELETE | `/:id` | JWT | Soft delete |
| POST | `/:id/toggle` | JWT | Toggle completion |
| PATCH | `/bulk` | JWT | Bulk update by IDs |
| POST | `/bulk-delete` | JWT | Bulk delete by IDs |

Query params: `search`, `priority` (low/medium/high), `completed`, `overdue`, `due_today`, `page`, `limit`

### Billing `/api/billing`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/checkout` | JWT | Create Stripe checkout session |
| POST | `/portal` | JWT | Create Stripe billing portal |
| POST | `/stripe-webhook` | — | Stripe signed webhook handler |
| GET | `/subscription` | JWT | Get active subscription |
| POST | `/cancel` | JWT | Cancel subscription |

### System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health/live` | — | Liveness probe |
| GET | `/api/health/ready` | — | Readiness probe (DB + Redis) |
| GET | `/api/health/info` | — | App version + environment |
| GET | `/metrics` | — | Prometheus metrics |
| GET | `/docs` | — | Swagger UI (non-production only) |
| GET | `/admin` | Admin | SQLAdmin panel |

The full, current list of routes is in [docs/openapi.json](docs/openapi.json). Regenerate it with `make openapi-export`.

---

## Authentication Flows

### JWT Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Postgres
    participant R as Redis

    C->>A: POST /api/auth/login
    A->>DB: verify credentials + check lockout
    A->>DB: store refresh token hash
    A-->>C: { access_token (15min), refresh_token (7d) }

    C->>A: GET /api/todos (Bearer access_token)
    A-->>C: 200 OK

    Note over C,A: access_token expires
    C->>A: POST /api/auth/refresh { refresh_token }
    A->>DB: verify + rotate refresh token
    A-->>C: new { access_token, refresh_token }
```

### Magic Link / OTP Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant R as Redis
    participant E as Resend Email

    C->>A: POST /api/auth/magic-link/request { email }
    A->>R: store token (TTL 10min)
    A->>E: send link email (async via Celery)
    A-->>C: 200 OK

    C->>A: POST /api/auth/magic-link/verify { token }
    A->>R: validate + delete token
    A-->>C: { access_token, refresh_token }
```

### OAuth2 Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant G as Google/GitHub

    C->>A: GET /api/auth/google
    A-->>C: 302 → Google OAuth consent
    C->>G: user consents
    G->>A: GET /api/auth/google/callback?code=...
    A->>G: exchange code for profile
    A->>A: upsert user (oauth_provider + provider_id)
    A-->>C: 302 → frontend URL + token pair
```

---

## Development

```bash
make dev              # hot reload dev server (host, no Docker for the API)
make lint             # ruff check
make lint-fix         # ruff check --fix
make format           # ruff format
make typecheck        # mypy
make check            # lint + format check + typecheck
make pre-commit-install   # install git hooks (see .pre-commit-config.yaml)
```

For local setup with and without Docker, test environment variables, and the migration workflow, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

### Database

```bash
make migrate                       # apply pending migrations (Docker)
make migrate-local                 # apply pending migrations (host)
make migration msg="add x table"   # generate new migration
make migrate-down                  # rollback one step
make seed                          # load dev data
make create-superuser EMAIL=you@example.com   # create or promote a superuser
make db-reset                      # drop + recreate + migrate (DESTRUCTIVE, dev only)
```

Migration `0000_baseline` creates the base tables, so `alembic upgrade head` works on an empty database. If you built a database with `create_all`, run `uv run alembic stamp head` instead of migrating. Run `uv run alembic check` after a model change to confirm that the models and migrations match.

Seed accounts:

| Email | Role | Password |
|---|---|---|
| `admin@example.com` | superuser | `FIRST_SUPERUSER_PASSWORD` (`changeme` in `.env.example`) |
| `alice@example.com`, `bob@example.com`, `charlie@example.com` | user | `password123` |

### Adding a module

```bash
make generate MODULE=myfeature
```

Scaffolds the new package under `app/api/<module>/` with `model.py`, `schemas.py`, `service.py`, `router.py`, `__init__.py`. See [FEATURE_GENERATION.md](FEATURE_GENERATION.md) for the full workflow.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | `development` / `production` / `test` |
| `SECRET_KEY` | — | Min 32 chars, required |
| `JWT_SECRET_KEY` | — | Min 32 chars, required |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async Postgres URL |
| `DATABASE_POOL_SIZE` | `20` | SQLAlchemy pool size |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `RESEND_API_KEY` | `""` | Email delivery |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth |
| `GITHUB_CLIENT_ID` | `""` | GitHub OAuth |
| `STRIPE_API_KEY` | `""` | Stripe payments |
| `STRIPE_WEBHOOK_SECRET` | `""` | Webhook signature verification |
| `ANTHROPIC_API_KEY` | `""` | Claude AI |
| `OPENAI_API_KEY` | `""` | OpenAI |
| `OTEL_ENABLED` | `false` | OpenTelemetry tracing |
| `SENTRY_DSN` | `""` | Sentry error tracking |
| `PROMETHEUS_ENABLED` | `true` | Prometheus `/metrics` |
| `STORAGE_DRIVER` | `local` | `local` or `s3` |
| `UPLOAD_MAX_SIZE_MB` | `50` | Max upload size |
| `WEBAUTHN_RP_ID` | `localhost` | Relying party domain |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Global rate limit |

Full reference: [`.env.example`](.env.example). Variables for optional services are in [docs/SERVICES.md](docs/SERVICES.md). `APP_VERSION` defaults to the version in `pyproject.toml`; set it only to override.

---

## Docker

```bash
make up                # postgres + redis + api
make up-celery         # + Celery worker and beat
make up-monitoring     # + Celery worker, beat, and Flower
make down
make logs
make status
```

Optional services (pgvector, RabbitMQ, Neo4j, SeaweedFS, Celery, Flower) each have a Compose profile and a Make target. See [docs/SERVICES.md](docs/SERVICES.md) for the full list.

Production image:

```bash
make build-prod                                  # build via docker-compose.prod.yml
docker build --target production -t my-api .     # or build the image alone
docker run -p 8100:8100 --env-file .env.prod my-api
```

In `production` mode: Swagger/ReDoc disabled, JSON logging, debug off, secret key validation enforced. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Testing

Tests use a **real database** (NullPool — no mocked ORM) and factories via `factory_boy`.

> **Note:** the tests run against `TEST_DATABASE_URL` (default: `DATABASE_URL` with `_test` added to the database name, created if missing). The database name must end with `_test`, so the tests never touch your dev database.

```bash
make test                # all tests
make test-unit           # fast, isolated
make test-integration    # real Postgres + Redis
make test-e2e            # full user journeys
make test-cov            # HTML report → htmlcov/index.html
```

Test markers: `unit`, `integration`, `e2e`, `slow`, `smoke`, `ml`.

For the required environment variables (`APP_ENV=test`, `RATE_LIMIT_ENABLED=false`, a test `DATABASE_URL`, and others) and a copy-paste setup, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#run-tests).

---

## Security

- `SECRET_KEY` min 32 chars — validated at boot in production
- `JWT_SECRET_KEY` separate from `SECRET_KEY`
- Passwords hashed with **bcrypt**
- Refresh tokens **hashed** before storage (SHA-256)
- Account **lockout** after 5 failed attempts (15-min window)
- Rate limiting on all auth endpoints
- CORS configured via `CORS_ORIGINS`
- **Security headers** on all responses (HSTS, CSP, X-Frame-Options)
- API keys hashed before storage
- SQL injection prevented via SQLAlchemy parameterized queries
- File uploads capped at `UPLOAD_MAX_SIZE_MB`
- Stripe webhook **signature verified** on every event

---

## Performance

- **asyncpg** driver — async I/O, no thread-pool blocking
- **Pydantic** response serialization — FastAPI serializes typed responses directly to JSON bytes
- **GZip** middleware — ~70% size reduction on JSON responses
- **structlog** JSON renderer — machine-parseable in production
- **Redis** for cache, OTP, lockout — avoids extra DB round-trips
- Connection pool: `DATABASE_POOL_SIZE=20`, `DATABASE_MAX_OVERFLOW=40`

---

## Further reading

| Doc | Contents |
|---|---|
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup with and without Docker, migrations, tests, pre-commit |
| [docs/SERVICES.md](docs/SERVICES.md) | Every Compose service: profile, Make target, ports, env vars |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagrams, middleware stack, data model, service layer |
| [docs/AUTH.md](docs/AUTH.md) | All auth flows with sequence diagrams, RBAC reference |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment, health checks, monitoring |
| [docs/RELEASING.md](docs/RELEASING.md) | Version bump, tag, and release workflow |
| [CHANGELOG.md](CHANGELOG.md) | Release notes for every version |
| [docs/AI_AGENTS.md](docs/AI_AGENTS.md) | Agent package layout, settings, adding an agent, `ml` queue |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Optional RabbitMQ service and the Django Ninja HTTP client |
| [docs/VECTOR.md](docs/VECTOR.md) | Optional pgvector service, embeddings schema example |
| [docs/GRAPH.md](docs/GRAPH.md) | Optional Neo4j graph database and client |
| [FEATURE_GENERATION.md](FEATURE_GENERATION.md) | How to scaffold a new API module |
| [.env.example](.env.example) | All environment variables with descriptions |
| [docs/openapi.json](docs/openapi.json) | Exported OpenAPI spec |
