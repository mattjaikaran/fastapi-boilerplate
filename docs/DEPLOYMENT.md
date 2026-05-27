# Deployment

Production deployment guide for the FastAPI Boilerplate.

---

## Docker Compose (recommended for most deployments)

### Development

```bash
make up            # postgres + redis + api
make up-celery     # add Celery worker
make up-monitoring # add Celery worker + Flower
```

Services started by `make up`:

| Service | Port | Notes |
|---|---|---|
| `api` | 8000 | FastAPI (uvicorn, hot reload in dev) |
| `db` | 5432 | PostgreSQL 17 |
| `redis` | 6379 | Redis 7 |
| `worker` | — | Celery worker (optional profile) |
| `beat` | — | Celery beat (optional profile) |
| `flower` | 5555 | Celery monitor (optional profile) |

### Production

```bash
docker compose -f docker-compose.prod.yml up -d
```

Production compose adds:
- Non-root user in container
- Memory limits on all services
- Restart policies (`unless-stopped`)
- No volume mounts for source code
- `APP_ENV=production` enforced

---

## Dockerfile Stages

```mermaid
graph TD
    BASE["base\nPython 3.13-slim + uv + system deps"] --> BUILDER
    BASE --> DEV
    BUILDER["builder\nuv sync --no-dev (prod deps only)"] --> PROD
    BASE --> CI

    DEV["development\nAll deps + --reload"]
    PROD["production\nMinimal runtime\nnon-root user\ncopy .venv from builder"]
    CI["ci\nTest runner stage"]
```

```bash
# Build production image
docker build -t my-api .

# Build specific stage
docker build --target development -t my-api:dev .
docker build --target ci -t my-api:ci .

# Run production
docker run \
  -p 8000:8000 \
  --env-file .env.prod \
  --restart unless-stopped \
  my-api
```

---

## Environment Configuration

### Required in Production

```bash
# App
APP_ENV=production
APP_WORKERS=4               # match CPU cores × 2

# Security — MUST be changed
SECRET_KEY=<64-char random string>
JWT_SECRET_KEY=<64-char random string, different from SECRET_KEY>

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/app_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://:password@redis-host:6379/0

# JWT
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# WebAuthn (must match prod domain)
WEBAUTHN_RP_ID=yourdomain.com
WEBAUTHN_ORIGIN=https://yourdomain.com

# CORS
CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

### Optional but Recommended

```bash
# Error tracking
SENTRY_DSN=https://...@sentry.io/...
SENTRY_TRACES_SAMPLE_RATE=0.1

# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
PROMETHEUS_ENABLED=true

# Email
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
EMAIL_FROM_NAME="My App"

# OAuth2
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
OAUTH_REDIRECT_FRONTEND_URL=https://yourdomain.com/auth/callback

# Stripe
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_DEFAULT_PRICE_ID=price_...

# File Storage
STORAGE_DRIVER=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
AWS_S3_BUCKET=my-app-uploads
UPLOAD_MAX_SIZE_MB=50

# AI
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Generate secrets:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Pre-Flight Checklist

```mermaid
graph TD
    A[Generate secrets] --> B[Set all required env vars]
    B --> C[Run migrations]
    C --> D[Create superuser]
    D --> E[Verify health endpoints]
    E --> F[Configure reverse proxy]
    F --> G[Enable TLS]
    G --> H[Set up monitoring]
    H --> I[Deploy]
```

```bash
# 1. Run migrations before starting the app
uv run alembic upgrade head

# 2. Create initial superuser (idempotent)
uv run python scripts/create_superuser.py

# 3. Verify
curl https://yourdomain.com/api/health/ready
# → { "data": { "db": "ok", "redis": "ok" } }
```

---

## Database Migrations

**Never use schema sync in production.** Always use Alembic migration files.

```bash
# Generate migration (from local dev)
make migration msg="add subscription_tiers table"

# Review generated file in migrations/versions/
# Commit to repo

# Apply in production (before new binary starts)
uv run alembic upgrade head

# Rollback one step if needed
uv run alembic downgrade -1
```

Migration files are named `YYYYMMDD_HHMM_<slug>.py`. Always review auto-generated migrations for:
- Missing indexes on FK columns
- NOT NULL columns on large tables (use multi-step: nullable → backfill → not null)
- `server_default` vs `default` semantics

---

## Health Checks

| Endpoint | Checks | Use |
|---|---|---|
| `GET /api/health/live` | Process alive | Kubernetes liveness probe |
| `GET /api/health/ready` | DB + Redis connectivity | Kubernetes readiness probe |
| `GET /api/health/info` | App version + env | Deployment verification |

Kubernetes probe config:

```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

---

## Reverse Proxy (Nginx)

```nginx
upstream api {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/ssl/certs/yourdomain.pem;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;

    # Forward real IP for rate limiting + logging
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Host $host;

    location / {
        proxy_pass http://api;
        proxy_read_timeout 300;
    }

    # WebSocket support
    location /api/ws/ {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Block admin in prod from public internet (optional)
    location /admin {
        allow 10.0.0.0/8;   # internal network only
        deny all;
        proxy_pass http://api;
    }
}
```

---

## Celery Workers

```bash
# Start worker (handles email, notifications, ml, webhooks queues)
celery -A app.workers.celery_app worker \
  --loglevel=info \
  -Q default,email,notifications,ml,webhooks \
  --concurrency=4

# Start beat (scheduled tasks)
celery -A app.workers.celery_app beat --loglevel=info

# Monitor via Flower
celery -A app.workers.celery_app flower --port=5555
```

Scheduled tasks (from `celery_app.py`):

| Task | Schedule | Description |
|---|---|---|
| `cleanup_expired_tokens` | Hourly | Remove expired refresh tokens + OTPs |
| `purge_old_audit_logs` | Daily | Archive/delete old audit entries |
| `expire_api_keys` | Hourly | Mark expired API keys as inactive |

---

## Observability Setup

### Prometheus + Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: fastapi
    static_configs:
      - targets: ["api:8000"]
    metrics_path: /metrics
    scrape_interval: 15s
```

Key metrics exposed:

| Metric | Type | Description |
|---|---|---|
| `http_request_duration_seconds` | Histogram | Request latency by method + path |
| `http_requests_total` | Counter | Total requests by status code |
| `http_requests_in_progress` | Gauge | Concurrent requests |

### OpenTelemetry

```bash
OTEL_ENABLED=true
OTEL_SERVICE_NAME=my-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

Auto-instrumented: FastAPI routes, SQLAlchemy queries. Traces exported via gRPC to your OTLP collector (Jaeger, Grafana Tempo, Honeycomb, etc.).

### Sentry

```bash
SENTRY_DSN=https://xxx@sentry.io/yyy
SENTRY_TRACES_SAMPLE_RATE=0.1    # 10% of requests traced
```

Captures unhandled exceptions and attaches user context (user ID, email).

---

## Performance Tuning

### Uvicorn Workers

```bash
# Rule of thumb: (2 × CPU_cores) + 1
APP_WORKERS=9   # for 4-core machine

# Or let uvicorn choose
uvicorn app.main:app --workers $(( 2 * $(nproc) + 1 ))
```

### Database Pool

```bash
DATABASE_POOL_SIZE=20       # per-process connections
DATABASE_MAX_OVERFLOW=40    # burst connections
```

Total max connections = `WORKERS × (POOL_SIZE + MAX_OVERFLOW)`. Ensure your Postgres `max_connections` is higher.

### Redis

```bash
REDIS_CACHE_TTL=300         # 5-minute default cache TTL
```

Use Redis Cluster or Sentinel for high availability.

---

## Security Hardening

- Set `APP_DEBUG=false` (enforced when `APP_ENV=production`)
- Rotate `SECRET_KEY` and `JWT_SECRET_KEY` periodically — this invalidates all sessions
- Set `ALLOWED_HOSTS` to your domain(s)
- Restrict `/admin` to internal network via Nginx (see above)
- Use secrets manager (AWS SSM, Vault, Doppler) rather than `.env` files on servers
- Enable Sentry for real-time exception alerts
- Set `UPLOAD_MAX_SIZE_MB` conservatively (default 50MB)
- Configure Stripe webhook secret — every webhook is verified with HMAC

---

## CI/CD

GitHub Actions workflows live in `.github/workflows/`. The `ci` Docker stage runs tests in a clean environment:

```bash
docker build --target ci -t my-api:ci .
docker run my-api:ci uv run pytest
```

Typical pipeline:

```mermaid
graph LR
    PUSH[git push] --> LINT[ruff + mypy]
    LINT --> TEST[pytest — unit + integration]
    TEST --> BUILD[docker build --target production]
    BUILD --> PUSH_REG[push to registry]
    PUSH_REG --> DEPLOY[deploy + alembic upgrade head]
    DEPLOY --> HEALTH[wait for /api/health/ready]
```
