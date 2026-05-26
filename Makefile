.DEFAULT_GOAL := help
.PHONY: help

# =============================================================================
# CONFIG
# =============================================================================
APP_NAME     := fastapi-app
PYTHON       := python
UV           := uv
DC           := docker compose
DC_PROD      := docker compose -f docker-compose.prod.yml
ALEMBIC      := $(UV) run alembic

# =============================================================================
# HELP
# =============================================================================
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# =============================================================================
# SETUP
# =============================================================================
install: ## Install all dependencies
	$(UV) sync

install-dev: ## Install dev + prod dependencies
	$(UV) sync --all-extras

setup: install copy-env ## Bootstrap: install deps + copy .env
	@echo "✓ Setup complete. Edit .env then run: make up"

copy-env: ## Copy .env.example to .env if not exists
	@[ -f .env ] || (cp .env.example .env && echo "✓ Created .env from .env.example")

quickstart: setup ## Clone-to-running: setup + start + migrate + seed
	$(MAKE) up
	@sleep 5
	$(MAKE) migrate
	$(MAKE) seed
	@echo "\n✓ App running at http://localhost:8000"
	@echo "✓ Docs at http://localhost:8000/docs"
	@echo "✓ Admin at http://localhost:8000/admin"

# =============================================================================
# DEVELOPMENT
# =============================================================================
dev: ## Run dev server with hot reload (no Docker)
	$(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-worker: ## Run Celery worker locally
	$(UV) run celery -A app.workers.celery_app worker --loglevel=debug -Q default,email,notifications,ml

dev-beat: ## Run Celery beat locally
	$(UV) run celery -A app.workers.celery_app beat --loglevel=debug

dev-flower: ## Run Flower (Celery monitor)
	$(UV) run celery -A app.workers.celery_app flower --port=5555

shell: ## Open Python shell with app context
	$(UV) run python -c "import asyncio; from app.config.database import async_session_factory; print('Session ready')"

# =============================================================================
# DOCKER
# =============================================================================
up: ## Start all services (dev)
	$(DC) up -d db redis api

up-celery: ## Start all services including Celery
	$(DC) --profile celery up -d

up-monitoring: ## Start all services including Flower
	$(DC) --profile celery --profile monitoring up -d

down: ## Stop all services
	$(DC) down

down-volumes: ## Stop all services and remove volumes (DESTRUCTIVE)
	$(DC) down -v

logs: ## Tail all logs
	$(DC) logs -f

logs-api: ## Tail API logs
	$(DC) logs -f api

logs-worker: ## Tail worker logs
	$(DC) logs -f worker

build: ## Build Docker images
	$(DC) build

build-prod: ## Build production Docker image
	$(DC) -f docker-compose.prod.yml build

restart: ## Restart API container
	$(DC) restart api

status: ## Show container status
	$(DC) ps

health: ## Check health endpoints
	@curl -sf http://localhost:8000/api/health/live | python -m json.tool || echo "API not reachable"

ready: ## Check readiness endpoint
	@curl -sf http://localhost:8000/api/health/ready | python -m json.tool || echo "API not ready"

# =============================================================================
# DATABASE
# =============================================================================
migrate: ## Run Alembic migrations
	$(DC) exec api alembic upgrade head

migrate-local: ## Run migrations locally (no Docker)
	$(ALEMBIC) upgrade head

migration: ## Create a new migration (usage: make migration msg="add users table")
	$(ALEMBIC) revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	$(ALEMBIC) downgrade -1

migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose

migrate-current: ## Show current migration
	$(ALEMBIC) current

db-shell: ## Open psql shell in Docker
	$(DC) exec db psql -U postgres -d app_db

db-dump: ## Dump database to file
	@mkdir -p backups
	$(DC) exec db pg_dump -U postgres app_db > backups/$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Dump saved to backups/"

db-restore: ## Restore database from file (usage: make db-restore file=backups/xxx.sql)
	$(DC) exec -T db psql -U postgres app_db < $(file)

db-reset: ## Drop and recreate database (DESTRUCTIVE)
	$(DC) exec db psql -U postgres -c "DROP DATABASE IF EXISTS app_db;"
	$(DC) exec db psql -U postgres -c "CREATE DATABASE app_db;"
	$(MAKE) migrate

seed: ## Seed database with initial data
	$(DC) exec api python scripts/seed_data.py

seed-local: ## Seed database locally
	$(UV) run python scripts/seed_data.py

# =============================================================================
# TESTING
# =============================================================================
test: ## Run all tests
	$(UV) run pytest

test-unit: ## Run unit tests only
	$(UV) run pytest -m unit

test-integration: ## Run integration tests only
	$(UV) run pytest -m integration

test-smoke: ## Run smoke tests only
	$(UV) run pytest -m smoke

test-e2e: ## Run E2E tests
	$(UV) run pytest -m e2e

test-ml: ## Run ML tests
	$(UV) run pytest -m ml

test-watch: ## Run tests in watch mode
	$(UV) run pytest --watch

test-cov: ## Run tests with coverage report
	$(UV) run pytest --cov=app --cov-report=html --cov-report=term-missing

test-fast: ## Run tests without slow ones
	$(UV) run pytest -m "not slow" -x

test-parallel: ## Run tests in parallel
	$(UV) run pytest -n auto

test-load: ## Run load tests (requires app running)
	$(UV) run locust -f scripts/load_tests.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless

# =============================================================================
# CODE QUALITY
# =============================================================================
lint: ## Run ruff linter
	$(UV) run ruff check app tests

lint-fix: ## Run ruff linter with auto-fix
	$(UV) run ruff check app tests --fix

format: ## Format code with ruff
	$(UV) run ruff format app tests

format-check: ## Check formatting without changes
	$(UV) run ruff format app tests --check

typecheck: ## Run mypy type checker
	$(UV) run mypy app

check: lint format-check typecheck ## Run all quality checks

pre-commit: ## Run pre-commit hooks
	$(UV) run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	$(UV) run pre-commit install

# =============================================================================
# OPENAPI
# =============================================================================
openapi-export: ## Export OpenAPI spec to JSON
	@mkdir -p docs
	$(UV) run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
	@echo "✓ OpenAPI spec saved to docs/openapi.json"

openapi-serve: ## Serve OpenAPI docs
	@echo "Docs: http://localhost:8000/docs"
	@echo "ReDoc: http://localhost:8000/redoc"

# =============================================================================
# ADMIN
# =============================================================================
create-superuser: ## Create a superuser account
	$(UV) run python scripts/create_superuser.py

# =============================================================================
# DEPENDENCIES
# =============================================================================
deps-update: ## Update all dependencies
	$(UV) lock --upgrade

deps-audit: ## Audit dependencies for vulnerabilities
	$(UV) run pip-audit

deps-tree: ## Show dependency tree
	$(UV) tree

# =============================================================================
# CI
# =============================================================================
ci: ## Run full CI pipeline locally
	$(MAKE) check
	$(MAKE) test-cov

# =============================================================================
# CLEANUP
# =============================================================================
clean: ## Remove Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml

clean-docker: ## Remove all Docker containers and images for this project
	$(DC) down --rmi all -v --remove-orphans

dev-reset: ## Full dev reset: stop → remove volumes → start → migrate → seed
	$(MAKE) down-volumes
	$(MAKE) up
	@sleep 8
	$(MAKE) migrate
	$(MAKE) seed
	@echo "✓ Dev environment reset complete"
