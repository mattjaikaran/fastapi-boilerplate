# Development guide

This guide shows you how to set up a local environment, run the app, manage migrations, and run tests. For a service-by-service list, see [SERVICES.md](SERVICES.md).

---

## Prerequisites

| Tool | Requirement |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Required. Manages Python and dependencies. |
| Python | 3.13. If your system Python is older, `uv sync` downloads 3.13. |
| Docker with the Compose plugin | Required for the recommended workflow. `scripts/setup.sh` stops when Docker Compose is missing. |
| `make` | Required to run the targets in this guide. |

---

## Set up

```bash
git clone <repo> && cd fastapi-boilerplate
./scripts/setup.sh      # check tools, run `uv sync`, create .env
./scripts/doctor.sh     # check the environment (optional)
```

`scripts/setup.sh` copies `.env.example` to `.env` and writes a generated `SECRET_KEY` and `JWT_SECRET_KEY`. It leaves an existing `.env` unchanged.

`make setup` is a shorter alternative. It runs `uv sync` and copies `.env.example` to `.env`, but it does not generate secrets. Replace the example secrets in `.env` yourself.

### Check your environment

```bash
./scripts/doctor.sh
```

The script reports these groups:

- **Toolchain**: uv, Python 3.13, Docker, Docker Compose, and the Docker daemon.
- **Environment**: `.env` exists, required variables are set, and the secrets differ from the example values.
- **Dependencies**: `.venv` exists, and `uv.lock` matches `pyproject.toml`.
- **Services**: Postgres and Redis containers are healthy, and the live and ready endpoints answer.
- **Code quality**: Ruff passes, and the pre-commit hook is installed.

A failed required check stops the run with a non-zero exit code. Warnings do not.

---

## Run the app

Choose one workflow.

### With Docker (recommended)

Docker runs Postgres, Redis, and the API.

```bash
make up               # db, redis, api on http://localhost:8100
make migrate          # alembic upgrade head inside the api container
make seed             # sample data
```

Or run all four steps (setup, start, migrate, seed) with `make quickstart`.

Useful commands:

```bash
make logs-api         # tail API logs
make status           # container status
make health           # liveness endpoint
make ready            # readiness endpoint (database and Redis)
make down             # stop services, keep data
```

To add optional services, see [SERVICES.md](SERVICES.md).

### Without Docker for the API

Run Postgres and Redis in Docker, and run the API on your machine. This gives you debugger access and faster restarts.

```bash
docker compose up -d db redis   # infrastructure only
make migrate-local              # alembic upgrade head on the host
make seed-local                 # sample data from the host
make dev                        # uvicorn with hot reload on port 8100
```

Do not run `make up` and `make dev` together. Both use port 8100 (`APP_PORT`).

The default `.env` values (`localhost:5432`, `localhost:6379`) match the published ports of the `db` and `redis` services.

If you run your own Postgres and Redis, set `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` in `.env`.

### Background workers on the host

```bash
make dev-worker       # Celery worker
make dev-beat         # Celery beat scheduler
make dev-flower       # Flower monitor
```

---

## Create a superuser

```bash
make create-superuser EMAIL=admin@example.com            # password from .env (FIRST_SUPERUSER_PASSWORD)
make create-superuser EMAIL=admin@example.com PASSWORD=...   # lands in your shell history; prefer the prompt
```

The target runs `scripts/create_superuser.py`. The make target passes `EMAIL` and `PASSWORD` to the script as the `SUPERUSER_EMAIL` and `SUPERUSER_PASSWORD` environment variables, so the password does not appear in the process list. `PASSWORD=...` still lands in your shell history. To avoid this, leave out `PASSWORD` and set an empty `FIRST_SUPERUSER_PASSWORD` so the script prompts (the prompt does not echo). The script reads the password from `--password`, then `SUPERUSER_PASSWORD`, then `FIRST_SUPERUSER_PASSWORD` (app settings, so `.env` applies). Because `.env.example` sets `FIRST_SUPERUSER_PASSWORD=changeme`, the script does not prompt with a default `.env`. With `APP_ENV=production`, the script refuses the password `changeme`. Without a terminal, the script exits with an error when a value is missing. It is idempotent: when the user exists, the script promotes the user to superuser and does not change the password unless you pass `--reset-password` to the script. If you omit `EMAIL`, the script uses `SUPERUSER_EMAIL` or `FIRST_SUPERUSER_EMAIL`. See the script docstring for all options.

`make seed` also creates a superuser from `FIRST_SUPERUSER_EMAIL` and `FIRST_SUPERUSER_PASSWORD`, plus sample users, todos, and organizations.

Seed accounts:

| Email | Role | Password |
|---|---|---|
| `admin@example.com` | superuser | `FIRST_SUPERUSER_PASSWORD` (`changeme` in `.env.example`) |
| `alice@example.com`, `bob@example.com`, `charlie@example.com` | user | `password123` |

---

## Migrations

Alembic manages the schema. Migration `0000_baseline` creates the base tables, so `alembic upgrade head` works on an empty database.

| Task | Command |
|---|---|
| Apply migrations (Docker) | `make migrate` |
| Apply migrations (host) | `make migrate-local` |
| Create a migration | `make migration msg="add widgets table"` |
| Roll back one step | `make migrate-down` |
| Show the current revision | `make migrate-current` |
| Show history | `make migrate-history` |

### Change a model

1. Edit the model in `app/api/<module>/model.py`.
2. For a new model, add its import to `register_all_models()` in `app/models/__init__.py`, so Alembic sees it. The generator does not do this for you.
3. Generate the migration: `make migration msg="describe the change"`.
4. Review the generated file in `migrations/versions/`. Autogenerate can miss renames, server defaults, and data changes.
5. Apply it: `make migrate`.
6. Confirm that the models and the schema match:

   ```bash
   uv run alembic check
   ```

   The command exits with a non-zero code when the models differ from the migrated schema. Run it before you commit a model change.

### Existing databases created without Alembic

If you built a database with `Base.metadata.create_all` (for example, from an earlier checkout), the tables exist but Alembic has no revision record. Mark the database as current instead of running the baseline:

```bash
uv run alembic stamp head
```

Run this only when the schema already matches the models. Otherwise, create a new database and run `make migrate`.

---

## Run tests

The test suite uses a real Postgres database and Redis. The `setup_db` fixture in `tests/conftest.py` creates all tables from the models at the start of the run and drops all tables at the end.

The suite never uses your dev database. It runs against `TEST_DATABASE_URL`. If you do not set it, it uses `DATABASE_URL` with `_test` added to the database name (`app_db` becomes `app_db_test`) and creates that database if it is missing. The suite refuses to start if the database name does not end with `_test`.

Example, as the CI workflow does (`.github/workflows/ci.yml`):

```bash
docker compose up -d db redis
# Optional: the test database is created automatically if it is missing.

export APP_ENV=test
export SECRET_KEY=local-test-secret-key-32-chars-min
export JWT_SECRET_KEY=local-test-jwt-secret-key-32-chars
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db_test
export CELERY_TASK_ALWAYS_EAGER=true
export RATE_LIMIT_ENABLED=false

uv run pytest
```

| Variable | Why the tests need it |
|---|---|
| `APP_ENV=test` | Selects test mode. |
| `SECRET_KEY`, `JWT_SECRET_KEY` | Each needs at least 32 characters. |
| `TEST_DATABASE_URL` | Optional. Database for the tests. The name must end with `_test`. Default: `DATABASE_URL` with `_test` added. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Default to local Redis. CI sets them explicitly. |
| `CELERY_TASK_ALWAYS_EAGER=true` | Runs Celery tasks in-process. |
| `RATE_LIMIT_ENABLED=false` | Stops rate limits from failing repeated requests. |

Make targets run the same suite through `uv run pytest`. They read your environment, so export the variables above first.

| Target | Runs |
|---|---|
| `make test` | All tests |
| `make test-unit` | `-m unit` |
| `make test-integration` | `-m integration` |
| `make test-e2e` | `-m e2e` |
| `make test-smoke` | `-m smoke` |
| `make test-fast` | Everything except `slow`, stops at the first failure |
| `make test-watch` | Re-runs fast tests when `app/` or `tests/` change |
| `make test-cov` | Coverage report in `htmlcov/` |
| `make test-parallel` | Runs tests in parallel |

Markers are `unit`, `integration`, `e2e`, `slow`, `smoke`, and `ml`. The `ml` tests run with `make test-ml`.

---

## Code quality

```bash
make lint             # ruff check
make lint-fix         # ruff check --fix
make format           # ruff format
make typecheck        # mypy
make check            # lint, format-check, typecheck
make agent-docs       # AGENTS.md exists, stays under 200 lines, links resolve
make ci               # check, then tests with coverage
```

### Pre-commit hooks

The repository includes `.pre-commit-config.yaml`. The hooks check whitespace, YAML and TOML syntax, merge conflicts, large files, and private keys. They also run Ruff on `app/` and `tests/`, check that `uv.lock` is current, and run the agent-doc check.

```bash
make pre-commit-install   # install the git hook once
make pre-commit           # run all hooks on all files
```

---

## Add a module

```bash
make generate MODULE=payments
```

See [FEATURE_GENERATION.md](../FEATURE_GENERATION.md).

---

## Export API specs

```bash
make openapi-export   # writes docs/openapi.json
make bruno-export     # Bruno collection from the OpenAPI spec (see the target output)
make postman-export   # docs/postman_collection.json (needs Node.js)
```

Run `make openapi-export` again after you change the API surface or release a new version, and commit the result.

---

## Dependencies

```bash
make deps-update      # upgrade versions in uv.lock
make deps-audit       # audit with pip-audit
make deps-tree        # show the dependency tree
```

After a dependency change, commit the updated `uv.lock`. CI runs `uv sync --locked` and fails when the lock file is stale.

---

## Release

See [RELEASING.md](RELEASING.md).
