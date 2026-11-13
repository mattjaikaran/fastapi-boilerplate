# Agent instructions

Backend instructions for this repository. The root AGENTS.md covers global rules
such as commits, branches, and secrets. Add a nested `AGENTS.md` only when a
package gains its own commands or rules; the nearest file then wins. Long
reference material stays in [docs/](docs/); keep this file under 200 lines.

## Project overview

Production-ready FastAPI + PostgreSQL boilerplate. Async-first: FastAPI,
SQLAlchemy 2 async with Alembic, Redis, Celery, JWT/OAuth2/WebAuthn auth,
Stripe billing, Resend email, SQLAdmin at `/admin`, and
Prometheus/Sentry/OpenTelemetry. Python 3.13; dependencies through `uv`; Docker
Compose for services.

| Path | Contents |
| --- | --- |
| `app/api/<module>/` | One API module: `model.py`, `schemas.py`, `service.py`, `router.py`. |
| `app/core/` | Middleware, exceptions, pagination, rate limiting, JWT and password security. |
| `app/services/` | Shared services: cache, email, storage, AI clients, graph, messaging, CRUD base. |
| `app/workers/` | Celery app and tasks: `email`, `notifications`, `ml`, `webhooks`, `maintenance`. |
| `app/agents/` | Pydantic AI and LangGraph agents (optional `agents` extra); see [docs/AI_AGENTS.md](docs/AI_AGENTS.md). |
| `migrations/versions/` | Alembic revisions, numbered linearly from `0000_baseline`. |
| `tests/` | pytest: `unit/`, `integration/`, `e2e/`, and `factories/`. |
| `scripts/` | Setup, doctor, seed, module generator, load tests, agent-doc check. |

System design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Auth flows and
RBAC: [docs/AUTH.md](docs/AUTH.md). Optional services:
[docs/SERVICES.md](docs/SERVICES.md). Release flow:
[docs/RELEASING.md](docs/RELEASING.md).

## Commands

Recipes are in the [justfile](justfile); `just` lists them. Each recipe runs the
[Makefile](Makefile) target of the same name, or the command it names.
Prerequisites: Python 3.13, [`uv`](https://docs.astral.sh/uv/), Docker with the
Compose plugin, `make`, and [`just`](https://just.systems/).

| Task | Command |
| --- | --- |
| Install dependencies and create `.env` | `just setup` |
| Check the environment | `just doctor` |
| Start Postgres, Redis, and the API | `just up` — API on http://localhost:8100 |
| Run the API on the host | `just dev` (Postgres and Redis in Docker) |
| Apply migrations | `just migrate` (Docker) or `just migrate-local` (host) |
| Seed sample data | `just seed` (Docker) or `just seed-local` (host) |
| Build the Docker image | `just build` (production image: `just build-prod`) |
| Lint and format check | `just lint`, `just format-check`; both plus mypy: `just check` |
| Type check | `just typecheck` |
| Smoke and e2e tests | `just test-smoke`, `just test-e2e` (need the database and Redis) |
| Pre-commit hooks | `just pre-commit-install` once, then `just pre-commit` |
| Check agent docs | `just agent-docs` |
| Scaffold a module | `just generate payments` |
| Health checks | `just health`, `just ready` |

`just up` and `just dev` both bind port 8100; never run both. Test environment
variables and the database setup are in
[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#run-tests).

## Code standards

- Ruff (line length 88, Python 3.13) and mypy with the pydantic plugin are
  configured in [pyproject.toml](pyproject.toml). Both must pass.
- Every API module follows the 5-file pattern and flows router → service →
  model; schemas stay at the HTTP boundary. Walkthrough:
  [FEATURE_GENERATION.md](FEATURE_GENERATION.md).
- Reuse the existing layers instead of adding a second convention: endpoints in
  `router.py`, business rules in `service.py`, persistence in `model.py`, shared
  errors from `app/core/exceptions/`.
- Register a new model in `register_all_models()` (`app/models/__init__.py`) and
  its router in `app/api/router.py`.
- Read configuration through `app.config.settings.settings`; never hard-code
  secrets, URLs, ports, or provider keys.
- `SECRET_KEY` and `JWT_SECRET_KEY` need at least 32 characters and must differ
  from the example values. Production also needs `DEBUG=False` and
  `ALLOWED_HOSTS`; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- Never disable authentication, rate limits, or permission checks to make a
  request pass.
- Type-annotate public functions and service methods. Keep business logic out
  of routers and middleware.
- Update the docs a change touches: [docs/](docs/) for guides, [README.md](README.md)
  for the API surface, and [CHANGELOG.md](CHANGELOG.md) for notable changes.

## Database and migrations

- Alembic owns the schema. After a model change, run
  `just migration "describe the change"`, review the generated file in
  `migrations/versions/`, then apply it.
- Keep one head and a linear chain. Never create a merge revision and never
  edit a revision that is already on `main`; add a new one instead.
- Run `just migration-check` before committing a model change; it must report
  no differences. Full workflow: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#migrations).

## Testing policy

- pytest only. The suite uses a real Postgres and Redis; `tests/conftest.py`
  creates the test database from `TEST_DATABASE_URL` and refuses a name that
  does not end in `_test`.
- A behavior change updates the test that covers it. Doc-only and tooling-only
  changes need the checks above, not a new test.
- Markers are `unit`, `integration`, `e2e`, `slow`, `smoke`, and `ml`; run them
  with the matching `just test-unit`, `just test-integration`, `just test-e2e`,
  `just test-smoke` or `just test-ml` recipe (for example `just test-smoke`).
- The agent-run gate runs lint, typecheck, build, smoke, and e2e only; it never
  runs the unit-test suite.

## Enforcement

- [.github/workflows/ci.yml](.github/workflows/ci.yml) runs
  `scripts/check_agent_docs.py` on every push and same-repo pull request, plus
  ruff, mypy, pytest, and the Docker build.
- [.pre-commit-config.yaml](.pre-commit-config.yaml) runs whitespace,
  YAML/TOML, merge-conflict, large-file and secret checks (including
  `detect-private-key`), ruff, `uv-lock`, and the agent-doc check.
