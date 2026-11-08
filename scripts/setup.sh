#!/usr/bin/env bash
# Bootstrap a local development environment.
# Compatible with bash 3.2 (macOS default).
set -euo pipefail

cd "$(dirname "$0")/.."

REQUIRED_PYTHON="3.13"

echo "=== FastAPI Postgres Boilerplate Setup ==="

fail() {
  echo "✗ $1" >&2
  exit 1
}

# --- Check requirements ------------------------------------------------------
command -v uv >/dev/null 2>&1 \
  || fail "uv is required. Install: https://docs.astral.sh/uv/getting-started/installation/"
echo "✓ uv $(uv --version | awk '{print $2}')"

# uv installs Python $REQUIRED_PYTHON on demand when the system Python is older.
if command -v python3 >/dev/null 2>&1 \
  && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)'; then
  echo "✓ Python $(python3 -c 'import platform; print(platform.python_version())')"
else
  echo "ℹ System Python is older than ${REQUIRED_PYTHON}. uv downloads ${REQUIRED_PYTHON} during sync."
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "✓ Docker Compose $(docker compose version --short)"
else
  fail "Docker with the Compose plugin is required. Install Docker Desktop or Docker Engine."
fi

# --- Install dependencies ----------------------------------------------------
echo "→ Installing Python dependencies..."
uv sync

# --- Create .env -------------------------------------------------------------
# Replace a KEY=value line with a freshly generated secret. Use a temp file
# because `sed -i` differs between macOS and GNU.
set_secret() {
  local key="$1"
  local value tmp
  value="$(openssl rand -hex 32 2>/dev/null || uv run python -c 'import secrets; print(secrets.token_hex(32))')"
  tmp="$(mktemp)"
  awk -v key="$key" -v value="$value" \
    'BEGIN { FS = OFS = "=" } $1 == key { print key "=" value; next } { print }' \
    .env >"$tmp"
  cat "$tmp" >.env
  rm -f "$tmp"
}

if [ ! -f .env ]; then
  cp .env.example .env
  set_secret SECRET_KEY
  set_secret JWT_SECRET_KEY
  echo "→ Created .env from .env.example with generated SECRET_KEY and JWT_SECRET_KEY"
else
  echo "✓ .env exists (left unchanged)"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Review .env (database, email, storage, OAuth settings)"
echo "  2. make up               — start Postgres, Redis and the API in Docker"
echo "  3. make migrate          — run database migrations"
echo "  4. make seed             — seed initial data"
echo "  5. make create-superuser — create an admin account (optional)"
echo "  6. make dev              — or run the dev server on the host"
echo ""
echo "Or run: make quickstart  (does steps 2-4)"
echo "Run ./scripts/doctor.sh to check your environment."
