#!/usr/bin/env bash
set -euo pipefail

echo "=== FastAPI Postgres Boilerplate Setup ==="

# Check requirements
command -v uv >/dev/null 2>&1 || { echo "uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required."; exit 1; }

# Install dependencies
echo "→ Installing Python dependencies..."
uv sync

# Copy .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "→ Created .env from .env.example"
  echo "  ⚠  Edit .env and set SECRET_KEY and JWT_SECRET_KEY before continuing"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env (set SECRET_KEY, JWT_SECRET_KEY, etc.)"
echo "  2. make up       — start Docker services"
echo "  3. make migrate  — run database migrations"
echo "  4. make seed     — seed initial data"
echo "  5. make dev      — start dev server"
echo ""
echo "Or run: make quickstart  (does all of the above)"
