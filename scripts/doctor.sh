#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo -e "${GREEN}✓${NC} $name"
    ((PASS++))
  else
    echo -e "${RED}✗${NC} $name"
    ((FAIL++))
  fi
}

warn() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo -e "${GREEN}✓${NC} $name"
  else
    echo -e "${YELLOW}⚠${NC} $name (optional)"
  fi
}

echo "=== FastAPI Boilerplate Doctor ==="
echo ""

echo "--- Runtime ---"
check "Python 3.13+" "python3 --version | grep -E '3\.(1[3-9]|[2-9][0-9])'"
check "uv installed" "uv --version"
check "Docker installed" "docker --version"
check "Docker Compose installed" "docker compose version"
check ".env file exists" "[ -f .env ]"
check "SECRET_KEY set" "grep -q 'SECRET_KEY=' .env && ! grep -q 'SECRET_KEY=$' .env"
check "JWT_SECRET_KEY set" "grep -q 'JWT_SECRET_KEY=' .env && ! grep -q 'JWT_SECRET_KEY=$' .env"

echo ""
echo "--- Services ---"
check "PostgreSQL reachable" "docker compose ps db | grep -q 'healthy'"
check "Redis reachable" "docker compose ps redis | grep -q 'healthy'"
warn "API reachable" "curl -sf http://localhost:8000/api/health/live"

echo ""
echo "--- Dependencies ---"
check "Python deps installed" "[ -d .venv ]"
warn "All deps up to date" "uv sync --check 2>/dev/null"

echo ""
echo "--- Code Quality ---"
warn "Ruff clean" "uv run ruff check app --quiet"
warn "No type errors" "uv run mypy app --quiet"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}All checks passed ($PASS/$((PASS+FAIL)))${NC}"
else
  echo -e "${RED}$FAIL check(s) failed. See above.${NC}"
  exit 1
fi
