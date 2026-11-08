#!/usr/bin/env bash
# Check the local development environment.
# Compatible with bash 3.2 (macOS default).
set -uo pipefail

cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    printf '%b\n' "${GREEN}✓${NC} $name"
    PASS=$((PASS + 1))
  else
    printf '%b\n' "${RED}✗${NC} $name"
    FAIL=$((FAIL + 1))
  fi
}

warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    printf '%b\n' "${GREEN}✓${NC} $name"
  else
    printf '%b\n' "${YELLOW}⚠${NC} $name (optional)"
  fi
}

# Succeed when KEY has a non-empty value in .env.
env_set() {
  grep -E "^$1=.+" .env >/dev/null 2>&1
}

# Succeed when KEY has at least 32 characters in .env (the app requires this).
env_min32() {
  local value
  value="$(grep -E "^$1=" .env | head -n 1 | cut -d= -f2-)"
  [ "${#value}" -ge 32 ]
}

echo "=== FastAPI Boilerplate Doctor ==="
echo ""

echo "--- Toolchain ---"
check "uv installed" "uv --version"
check "Python 3.13+ available (via uv or system)" \
  "uv run --quiet python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)'"
check "Docker installed" "docker --version"
check "Docker Compose installed" "docker compose version"
check "Docker daemon running" "docker info"

echo ""
echo "--- Environment ---"
check ".env file exists" "[ -f .env ]"
if [ -f .env ]; then
  check "SECRET_KEY set (32+ characters)" "env_min32 SECRET_KEY"
  check "JWT_SECRET_KEY set" "env_set JWT_SECRET_KEY"
  check "DATABASE_URL set" "env_set DATABASE_URL"
  check "REDIS_URL set" "env_set REDIS_URL"
  warn "SECRET_KEY is not the example value" \
    "! grep -q '^SECRET_KEY=change-me' .env"
  warn "JWT_SECRET_KEY is not the example value" \
    "! grep -q '^JWT_SECRET_KEY=change-me' .env"
fi

echo ""
echo "--- Dependencies ---"
check "Python deps installed (.venv)" "[ -d .venv ]"
warn "Lockfile matches pyproject.toml" "uv lock --check"
warn "Environment in sync with lockfile" "uv sync --check"

echo ""
echo "--- Services ---"
warn "PostgreSQL container healthy" "docker compose ps db | grep -q healthy"
warn "Redis container healthy" "docker compose ps redis | grep -q healthy"
warn "API live (http://localhost:8100/api/health/live)" \
  "curl -sf http://localhost:8100/api/health/live"
warn "API ready (http://localhost:8100/api/health/ready)" \
  "curl -sf http://localhost:8100/api/health/ready"

echo ""
echo "--- Code quality ---"
warn "Ruff clean" "uv run ruff check app tests --quiet"
warn "Formatting clean" "uv run ruff format app tests --check --quiet"
warn "pre-commit hooks installed" "[ -f .git/hooks/pre-commit ]"

echo ""
if [ "$FAIL" -eq 0 ]; then
  printf '%b\n' "${GREEN}All required checks passed ($PASS/$((PASS + FAIL)))${NC}"
else
  printf '%b\n' "${RED}$FAIL required check(s) failed. See above.${NC}"
  exit 1
fi
