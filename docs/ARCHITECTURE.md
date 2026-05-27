# Architecture

Technical deep-dive into the FastAPI Boilerplate system design.

---

## System Context

```mermaid
C4Context
    title System Context

    Person(user, "End User", "Web or mobile client")
    Person(admin, "Admin", "Internal operator")
    Person(dev, "Developer", "API consumer / integrator")

    System(api, "FastAPI Boilerplate", "Async REST API + WebSocket backend")

    System_Ext(stripe, "Stripe", "Payments")
    System_Ext(resend, "Resend", "Transactional email")
    System_Ext(google, "Google OAuth", "SSO")
    System_Ext(github, "GitHub OAuth", "SSO")
    System_Ext(anthropic, "Anthropic", "Claude AI")
    System_Ext(openai, "OpenAI", "GPT models")
    System_Ext(s3, "AWS S3", "File storage")
    System_Ext(sentry, "Sentry", "Error tracking")
    System_Ext(otel, "OTLP Collector", "Distributed tracing")

    Rel(user, api, "HTTPS / WSS")
    Rel(admin, api, "HTTPS /admin")
    Rel(dev, api, "HTTPS + API Key")
    Rel(api, stripe, "REST")
    Rel(api, resend, "REST")
    Rel(api, google, "OAuth2")
    Rel(api, github, "OAuth2")
    Rel(api, anthropic, "REST")
    Rel(api, openai, "REST")
    Rel(api, s3, "AWS SDK")
    Rel(api, sentry, "SDK")
    Rel(api, otel, "gRPC")
```

---

## Application Layers

```mermaid
graph TB
    subgraph HTTP["HTTP Layer"]
        ASGI[Uvicorn ASGI Server]
    end

    subgraph MW["Middleware Stack (applied top → bottom)"]
        direction TB
        M1[SecurityHeadersMiddleware — HSTS, CSP, X-Frame-Options]
        M2[RequestIDMiddleware — X-Request-ID on every request]
        M3[ResponseEnvelopeMiddleware — wraps all responses]
        M4[RateLimitMiddleware — slowapi per-endpoint limits]
        M5[LoggingMiddleware — structured request/response logs]
        M6[GZipMiddleware — compress responses > 1KB]
        M7[CORSMiddleware — cross-origin policy]
        M8[SessionMiddleware — required by SQLAdmin]
        M1 --> M2 --> M3 --> M4 --> M5 --> M6 --> M7 --> M8
    end

    subgraph ROUTES["Route Layer"]
        ROUTER[api_router /api]
        subgraph MODS["18 Modules"]
            AUTH[auth]
            USERS[users]
            ORGS[organizations]
            TODOS[todos]
            BILLING[billing]
            FF[feature_flags]
            NOTIF[notifications]
            AUDIT[audit]
            KEYS[api_keys]
            FILES[files]
            JOBS[jobs]
            HOOKS[webhooks]
            SEARCH[search]
            HEALTH[health]
            AI[ai]
            WS[ws]
        end
    end

    subgraph SVC["Service Layer"]
        BASE[CRUDService base — generic create/read/update/delete]
        CACHE[CacheService — Redis]
        EMAIL[EmailService — Resend]
        STORAGE[StorageService — local/S3]
        AI_SVC[AI clients — Anthropic + OpenAI]
    end

    subgraph DATA["Data Layer"]
        ORM[SQLAlchemy 2 async models]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
    end

    ASGI --> MW --> ROUTES
    ROUTES --> SVC
    SVC --> DATA
```

---

## Module Structure

Every API module follows the same 5-file pattern:

```
app/api/<module>/
├── __init__.py     — public exports
├── model.py        — SQLAlchemy ORM model(s)
├── schemas.py      — Pydantic request/response models
├── service.py      — business logic (extends CRUDService)
└── router.py       — FastAPI endpoints
```

```mermaid
classDiagram
    class CRUDService {
        +model: Type[M]
        +create(db, obj_in) M
        +get(db, id) M
        +get_multi(db, skip, limit) list~M~
        +update(db, db_obj, obj_in) M
        +delete(db, id) M
    }

    class TodoService {
        +search(db, query) list~Todo~
        +get_stats(db, user_id) TodoStats
        +bulk_update(db, ids, data) list~Todo~
    }

    class UserService {
        +get_by_email(db, email) User
        +create_api_key(db, user_id, name) APIKey
        +list_api_keys(db, user_id) list~APIKey~
    }

    class AuthService {
        +register(db, data) User
        +login(db, email, password) TokenPair
        +refresh(db, token) TokenPair
        +request_otp(db, email, purpose) void
        +verify_otp(db, email, code) bool
    }

    CRUDService <|-- TodoService
    CRUDService <|-- UserService
    AuthService --> UserService
```

---

## Data Model

```mermaid
erDiagram
    User {
        uuid id PK
        string email UK
        string password_hash
        string role
        bool is_active
        bool is_verified
        bool totp_enabled
        string oauth_provider
        string oauth_provider_id
        datetime deleted_at
        datetime created_at
    }

    RefreshToken {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        datetime expires_at
        bool revoked
    }

    OTP {
        uuid id PK
        uuid user_id FK
        string code_hash
        string purpose
        datetime expires_at
        bool used
    }

    WebAuthnCredential {
        uuid id PK
        uuid user_id FK
        string credential_id UK
        bytes public_key
        int sign_count
        string device_name
        bool backup_eligible
    }

    APIKey {
        uuid id PK
        uuid user_id FK
        string key_hash UK
        string name
        datetime last_used_at
        datetime expires_at
    }

    Organization {
        uuid id PK
        uuid owner_id FK
        string name
        string slug UK
        datetime deleted_at
    }

    OrganizationMember {
        uuid id PK
        uuid org_id FK
        uuid user_id FK
        string role
    }

    FeatureFlag {
        uuid id PK
        string key UK
        string type
        bool enabled
        float percentage
        json variants
    }

    BillingCustomer {
        uuid id PK
        uuid user_id FK
        string stripe_customer_id UK
    }

    Subscription {
        uuid id PK
        uuid user_id FK
        string stripe_subscription_id UK
        string status
        string price_id
        datetime current_period_end
    }

    AuditLog {
        uuid id PK
        uuid user_id FK
        string action
        string resource_type
        uuid resource_id
        json changes
        string ip_address
    }

    Notification {
        uuid id PK
        uuid user_id FK
        string title
        string body
        bool read
        string type
    }

    WebhookEvent {
        uuid id PK
        string event_type
        string url
        json payload
        string status
        int attempt_count
    }

    Job {
        uuid id PK
        uuid user_id FK
        string task_name
        string status
        json result
        string error
    }

    User ||--o{ RefreshToken : has
    User ||--o{ OTP : has
    User ||--o{ WebAuthnCredential : has
    User ||--o{ APIKey : has
    User ||--o{ OrganizationMember : belongs_to
    User ||--o{ Notification : receives
    User ||--o{ AuditLog : generates
    User ||--|| BillingCustomer : has
    User ||--o{ Subscription : has
    Organization ||--o{ OrganizationMember : has
```

---

## Background Worker Architecture

```mermaid
graph LR
    subgraph App["FastAPI App"]
        ENDPOINT[API Endpoint]
        TASK[.delay() / .apply_async()]
    end

    subgraph Broker["Redis (db=1)"]
        QUEUE_EMAIL[email queue]
        QUEUE_NOTIF[notifications queue]
        QUEUE_ML[ml queue]
        QUEUE_HOOKS[webhooks queue]
        QUEUE_DEFAULT[default queue]
    end

    subgraph Worker["Celery Worker"]
        EMAIL_TASK[send_email]
        NOTIF_TASK[deliver_notification]
        ML_TASK[run_ml_task]
        HOOK_TASK[deliver_webhook]
    end

    subgraph Beat["Celery Beat (scheduled)"]
        CLEANUP[cleanup_expired_tokens — hourly]
        PURGE[purge_old_audit_logs — daily]
        KEY_EXP[expire_api_keys — hourly]
    end

    subgraph Results["Redis (db=2)"]
        RESULT[task results]
    end

    ENDPOINT --> TASK
    TASK --> QUEUE_EMAIL
    TASK --> QUEUE_NOTIF
    TASK --> QUEUE_ML
    TASK --> QUEUE_HOOKS
    QUEUE_EMAIL --> EMAIL_TASK
    QUEUE_NOTIF --> NOTIF_TASK
    QUEUE_ML --> ML_TASK
    QUEUE_HOOKS --> HOOK_TASK
    Beat --> QUEUE_DEFAULT
    Worker --> RESULT
```

---

## Middleware Request Lifecycle

```mermaid
sequenceDiagram
    participant C as Client
    participant SEC as SecurityHeaders
    participant RID as RequestID
    participant ENV as ResponseEnvelope
    participant RL as RateLimit
    participant LOG as Logging
    participant GZ as GZip
    participant CORS as CORS
    participant H as Handler

    C->>SEC: HTTP Request
    SEC->>RID: pass through
    RID->>ENV: attach X-Request-ID
    ENV->>RL: pass through
    RL->>LOG: check limit (Redis)
    LOG->>GZ: log request start
    GZ->>CORS: pass through
    CORS->>H: validate origin
    H-->>CORS: 200 Response
    CORS-->>GZ: pass through
    GZ-->>LOG: compress if > 1KB
    LOG-->>ENV: log response
    ENV-->>RL: wrap in envelope
    RL-->>RID: set X-RateLimit-* headers
    RID-->>SEC: pass through
    SEC-->>C: add security headers
```

---

## Security Architecture

```mermaid
graph TD
    subgraph Perimeter["Perimeter Controls"]
        CORS_P[CORS policy]
        RATE[Rate limiting per endpoint]
        HEADS[Security headers — HSTS, CSP, X-Frame-Options]
    end

    subgraph AuthZ["Authentication"]
        JWT_A[JWT Bearer token — 15min TTL]
        REFRESH[Refresh token — 7d, single-use, hashed]
        APIKEY[API Key — hashed, scoped]
        OAUTH[OAuth2 — Google, GitHub]
        PASSKEY[WebAuthn passkey]
    end

    subgraph AuthN["Authorization"]
        RBAC[RBAC — user / admin / superuser]
        ORG[Org membership — owner / admin / member]
    end

    subgraph Protection["Data Protection"]
        BCRYPT[Passwords — bcrypt]
        SHA[Tokens/keys — SHA-256 stored hash]
        LOCKOUT[Account lockout — 5 attempts / 15min]
        PARAMQ[SQL — parameterized queries only]
    end

    Perimeter --> AuthZ
    AuthZ --> AuthN
    AuthN --> Protection
```

---

## Observability Stack

```mermaid
graph LR
    subgraph App["FastAPI App"]
        LOG[structlog — JSON in prod]
        TRACE[OTel instrumentation]
        ERR[Sentry SDK]
        METRIC[Prometheus instrumentator]
    end

    subgraph Outputs["Telemetry Outputs"]
        STDOUT[stdout / log aggregator]
        OTLP[OTLP Collector → Jaeger/Tempo]
        SENTRY_BE[Sentry backend]
        PROM_BE[Prometheus → Grafana]
    end

    LOG --> STDOUT
    TRACE --> OTLP
    ERR --> SENTRY_BE
    METRIC --> PROM_BE
```

Every request gets:
- `X-Request-ID` header (generated by `RequestIDMiddleware`)
- Structured log entry with `request_id`, `method`, `path`, `status_code`, `duration_ms`
- OTel span (if `OTEL_ENABLED=true`)
- Prometheus histogram entry (`http_request_duration_seconds`)
