# Authentication & Authorization

Complete reference for all authentication methods and authorization patterns.

---

## Auth Methods at a Glance

| Method | Use Case | Token Type |
|---|---|---|
| Email + Password | Standard login | JWT pair |
| Refresh Token | Extend session | Rotated JWT pair |
| OTP (email code) | Verification, 2FA, password reset | One-time code |
| Magic Link | Passwordless login | Signed token |
| TOTP | Authenticator app 2FA | 6-digit TOTP |
| Google OAuth2 | Social login | JWT pair |
| GitHub OAuth2 | Social login | JWT pair |
| WebAuthn / Passkey | Biometric / hardware key | JWT pair |
| API Key | Service-to-service | Static key |

---

## JWT Token Flow

Access tokens live 15 minutes. Refresh tokens rotate on every use (single-use, stored as SHA-256 hash).

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Postgres
    participant R as Redis

    Note over C,R: Login
    C->>A: POST /api/auth/login { email, password }
    A->>DB: load user, check lockout counter (Redis)
    A->>A: bcrypt.verify(password, hash)
    A->>DB: store refresh_token SHA-256 hash
    A-->>C: 200 { access_token, refresh_token, user }

    Note over C,A: Authenticated request
    C->>A: GET /api/todos Authorization: Bearer <access_token>
    A->>A: verify JWT signature + expiry
    A-->>C: 200 { data }

    Note over C,A: Token refresh
    C->>A: POST /api/auth/refresh { refresh_token }
    A->>DB: lookup hash, verify not revoked + not expired
    A->>DB: delete old token, insert new token
    A-->>C: 200 { access_token, refresh_token }

    Note over C,A: Logout
    C->>A: POST /api/auth/logout { refresh_token }
    A->>DB: mark token revoked
    A-->>C: 204
```

Token payload:

```json
{
  "sub": "<user-uuid>",
  "role": "user",
  "exp": 1234567890,
  "iat": 1234567890,
  "jti": "<uuid>"
}
```

---

## OTP Flow

Used for email verification, password reset, and 2FA challenges.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Postgres
    participant R as Redis
    participant E as Resend Email

    C->>A: POST /api/auth/request-otp { email, purpose }
    A->>A: generate 6-digit code
    A->>DB: store OTP (hashed, TTL=10min)
    A->>E: enqueue email via Celery
    A-->>C: 200 OK

    C->>A: POST /api/auth/verify-otp { email, code, purpose }
    A->>DB: lookup OTP for email+purpose
    A->>A: verify hash, check expiry, check not used
    A->>DB: mark OTP used
    A-->>C: 200 { verified: true }
```

OTP purposes: `email_verification` · `password_reset` · `two_factor` · `magic_link`

---

## Magic Link Flow

Passwordless authentication via a signed, single-use token.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant R as Redis
    participant E as Resend Email

    C->>A: POST /api/auth/magic-link/request { email }
    A->>A: generate signed token (UUID + HMAC)
    A->>R: store token → user_id (TTL=10min)
    A->>E: enqueue magic link email
    A-->>C: 200 OK

    Note over C: user clicks link in email

    C->>A: POST /api/auth/magic-link/verify { token }
    A->>R: lookup token → user_id
    A->>R: delete token (single-use)
    A->>A: issue JWT pair
    A-->>C: 200 { access_token, refresh_token }
```

---

## TOTP (Authenticator App)

Standard TOTP (RFC 6238). Compatible with Google Authenticator, Authy, 1Password, etc.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Postgres

    Note over C,DB: Setup
    C->>A: POST /api/auth/totp/setup (JWT required)
    A->>A: generate TOTP secret (pyotp)
    A->>DB: store secret (encrypted)
    A-->>C: { secret, qr_code_url, backup_codes }

    Note over C: user scans QR in authenticator app

    C->>A: POST /api/auth/totp/verify { code }
    A->>DB: load secret
    A->>A: pyotp.verify(code, window=1)
    A->>DB: set totp_enabled=true
    A-->>C: 200 { enabled: true }

    Note over C,DB: Login with TOTP
    C->>A: POST /api/auth/login { email, password }
    A-->>C: 200 { requires_totp: true, temp_token }
    C->>A: POST /api/auth/totp/challenge { temp_token, code }
    A->>A: verify TOTP code
    A-->>C: 200 { access_token, refresh_token }
```

---

## OAuth2 Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant P as Provider (Google/GitHub)
    participant DB as Postgres

    C->>A: GET /api/auth/google
    A-->>C: 302 → Google consent screen

    Note over C,P: User authorizes the app

    P->>A: GET /api/auth/google/callback?code=...&state=...
    A->>P: POST /oauth/token (exchange code)
    P-->>A: { access_token }
    A->>P: GET /userinfo
    P-->>A: { email, name, picture, id }

    A->>DB: upsert User (oauth_provider=google, oauth_provider_id=...)
    A->>A: issue JWT pair
    A-->>C: 302 → OAUTH_REDIRECT_FRONTEND_URL?access_token=...&refresh_token=...
```

Provider fields stored on `User`:
- `oauth_provider` — `google` | `github`
- `oauth_provider_id` — provider's user ID

---

## WebAuthn / Passkeys

Biometric or hardware-key authentication via FIDO2 / WebAuthn.

```mermaid
sequenceDiagram
    participant C as Client (browser)
    participant A as API
    participant DB as Postgres

    Note over C,DB: Registration
    C->>A: POST /api/auth/webauthn/register/begin (JWT)
    A->>A: generate challenge (py-webauthn)
    A->>A: store challenge in session
    A-->>C: { challenge, rp, user, pubKeyCredParams }

    C->>C: navigator.credentials.create(options)
    C->>A: POST /api/auth/webauthn/register/complete { credential }
    A->>A: verify attestation + challenge
    A->>DB: store credential_id, public_key, sign_count
    A-->>C: 200 { credential_id, device_name }

    Note over C,DB: Authentication
    C->>A: POST /api/auth/webauthn/authenticate/begin { username }
    A->>DB: load credential IDs for user
    A->>A: generate challenge
    A-->>C: { challenge, allowCredentials }

    C->>C: navigator.credentials.get(options)
    C->>A: POST /api/auth/webauthn/authenticate/complete { assertion }
    A->>DB: load credential, verify signature + sign_count
    A->>DB: update sign_count (replay attack protection)
    A-->>C: 200 { access_token, refresh_token }
```

Config required:

```env
WEBAUTHN_RP_ID=yourdomain.com      # must match browser origin
WEBAUTHN_RP_NAME="My App"
WEBAUTHN_ORIGIN=https://yourdomain.com
```

---

## API Key Authentication

For service-to-service or CLI access. Keys are shown once on creation — only the SHA-256 hash is stored.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant DB as Postgres

    Note over C,DB: Create key
    C->>A: POST /api/users/me/api-keys { name } (JWT)
    A->>A: generate 32-byte random key
    A->>DB: store SHA-256(key), name, user_id
    A-->>C: 201 { key: "ak_...", name, id }
    Note over C: key shown once — save it now

    Note over C,DB: Use key
    C->>A: GET /api/todos X-Api-Key: ak_...
    A->>A: SHA-256(key) lookup in DB
    A->>DB: update last_used_at
    A-->>C: 200 { data }
```

---

## Role-Based Access Control

Three built-in roles on the `User` model:

```mermaid
graph TD
    SUPERUSER[superuser]
    ADMIN[admin]
    USER[user]

    SUPERUSER -->|inherits| ADMIN
    ADMIN -->|inherits| USER

    USER --> U1[own profile CRUD]
    USER --> U2[create todos / orgs]
    USER --> U3[manage own API keys]
    USER --> U4[billing / subscription]

    ADMIN --> A1[list / read all users]
    ADMIN --> A2[update any user]
    ADMIN --> A3[manage feature flags]
    ADMIN --> A4[view all audit logs]

    SUPERUSER --> S1[delete users]
    SUPERUSER --> S2[manage all orgs]
    SUPERUSER --> S3[access /admin panel]
```

Organization-level roles (per `OrganizationMember.role`):

| Role | Permissions |
|---|---|
| `owner` | All org ops including delete |
| `admin` | Add/remove members, update org |
| `member` | Read org and member list |

### Dependency Usage

```python
from app.api.auth.dependencies import CurrentUser, AdminUser, SuperUser

@router.get("/")
async def list_users(user: AdminUser) -> list[UserResponse]:
    ...

@router.delete("/:id")
async def delete_user(user: SuperUser) -> None:
    ...
```

---

## Account Lockout

After 5 consecutive failed login attempts, the account is locked for 15 minutes. Lockout state is tracked in Redis.

```mermaid
stateDiagram-v2
    [*] --> Active
    Active --> Active: successful login (reset counter)
    Active --> Warning: failed attempt (counter < 5)
    Warning --> Active: successful login (reset counter)
    Warning --> Locked: 5th failed attempt
    Locked --> Active: 15 minutes elapsed
    Locked --> Locked: any login attempt (returns 423)
```

---

## Password Reset

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API
    participant E as Email

    C->>A: POST /api/auth/forgot-password { email }
    A->>A: generate OTP (purpose=password_reset)
    A->>E: send OTP email
    A-->>C: 200 OK (always, even if email not found)

    C->>A: POST /api/auth/reset-password { email, code, new_password }
    A->>A: verify OTP (purpose=password_reset)
    A->>A: bcrypt.hash(new_password)
    A->>A: revoke all refresh tokens for user
    A-->>C: 200 OK
```

The `200 OK` on forgot-password regardless of email existence prevents user enumeration.

---

## Response Format

All auth endpoints return a consistent envelope:

```json
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "role": "user",
      "is_verified": true
    }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "status": 401
  }
}
```
