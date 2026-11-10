# Agent instructions

Single source of agent instructions for this repository. Any agent, editor, or
tool reads this file; a `CLAUDE.md` may only import it. Add a nested `AGENTS.md`
only when a package gains its own commands or rules; the nearest file then
wins. Long reference material stays in [docs/](docs/); keep this file under 200
lines.

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
[docs/SERVICES.md](docs/SERVICES.md).

## Commands

Targets are defined in the [Makefile](Makefile); `make help` lists them.
Prerequisites: Python 3.13, [`uv`](https://docs.astral.sh/uv/), Docker with the
Compose plugin, and `make`.

| Task | Command |
| --- | --- |
| Install dependencies and create `.env` | `./scripts/setup.sh` (or `make setup`, which copies `.env` without secrets) |
| Check the environment | `./scripts/doctor.sh` |
| Start Postgres, Redis, and the API | `make up` — API on http://localhost:8100 |
| Run the API on the host | `make dev` (Postgres and Redis in Docker) |
| Apply migrations | `make migrate` (Docker) or `make migrate-local` (host) |
| Seed sample data | `make seed` (Docker) or `make seed-local` (host) |
| Build the Docker image | `make build` (production image: `make build-prod`) |
| Lint and format check | `make lint`, `make format-check`; both plus mypy: `make check` |
| Type check | `make typecheck` |
| Smoke and e2e tests | `make test-smoke`, `make test-e2e` (need the database and Redis) |
| Pre-commit hooks | `make pre-commit-install` once, then `make pre-commit` |
| Check agent docs | `make agent-docs` |
| Scaffold a module | `make generate MODULE=payments` |
| Health checks | `make health`, `make ready` |

`make up` and `make dev` both bind port 8100; never run both. Test environment
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
- Type-annotate public functions and service methods. Keep business logic out
  of routers and middleware.
- Update the docs a change touches: [docs/](docs/) for guides, [README.md](README.md)
  for the API surface, and [CHANGELOG.md](CHANGELOG.md) for notable changes.

## Database and migrations

- Alembic owns the schema. After a model change, run
  `make migration msg="describe the change"`, review the generated file in
  `migrations/versions/`, then apply it.
- Keep one head and a linear chain. Never create a merge revision and never
  edit a revision that is already on `main`; add a new one instead.
- Run `uv run alembic check` before committing a model change; it must report
  no differences. Full workflow: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md#migrations).

## Testing policy

- pytest only. The suite uses a real Postgres and Redis; `tests/conftest.py`
  creates the test database from `TEST_DATABASE_URL` and refuses a name that
  does not end in `_test`.
- A behavior change updates the test that covers it. Doc-only and tooling-only
  changes need the checks above, not a new test.
- Markers are `unit`, `integration`, `e2e`, `slow`, `smoke`, and `ml`; run them
  with the matching `make test-unit`, `make test-integration`, `make test-e2e`,
  `make test-smoke` or `make test-ml` target (for example `make test-smoke`).
- The agent-run gate runs lint, typecheck, build, smoke, and e2e only; it never
  runs the unit-test suite. Do not add or change unit tests to satisfy it.

## Git and commits

- Conventional Commits: `type(scope): Imperative summary` with a subject of at
  most 50 characters and a body wrapped at 72. Types: `feat`, `fix`, `chore`,
  `docs`, `test`, `refactor`, `ci`, `build`, `style`, `perf`.
- One logical change per commit; leave `git status` clean before you stop.
- Do not rewrite history on shared branches or force-push them.
- Release flow: [docs/RELEASING.md](docs/RELEASING.md).

## Agent-run spec workflow

- Work only the issue or spec you were given; its acceptance criteria define
  done. Stay inside the files the task names.
- Branch `agent/issue-<n>`. The pull request title is one plain-English,
  sentence-case, imperative line of at most 72 characters, with no spec ID and
  no `type(scope):` prefix.
- Do not push or open the pull request yourself; the agent-run gate pushes
  after the static checks, smoke tests, and e2e tests pass.
- Specs, when a task ships one, live under `tasks/specs/`; its `README.md`
  names the files each spec owns. This repository has none yet, so agent-run
  tasks here are GitHub issues.
- Verify with the commands above and report the command and its result.

## Security

- Secrets come from the environment. `.env` is gitignored; copy
  [.env.example](.env.example) and never commit a real key. Pre-commit runs
  `detect-private-key`.
- `SECRET_KEY` and `JWT_SECRET_KEY` need at least 32 characters and must differ
  from the example values. Production also needs `DEBUG=False` and
  `ALLOWED_HOSTS`; see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- Never log tokens, passwords, or API keys. Never disable authentication, rate
  limits, or permission checks to make a request pass.
- Keep personal agent files (`.claude/settings.local.json`, `.mcp.local.json`)
  out of git.

## Skills

No skills are defined yet. If one is added, it lives in
`.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter, so
only the description loads until the skill is used. Procedures go in skills;
facts stay here.

## Enforcement

- [.github/workflows/ci.yml](.github/workflows/ci.yml) runs
  `scripts/check_agent_docs.py` on every push and same-repo pull request, plus
  ruff, mypy, pytest, and the Docker build.
- [.pre-commit-config.yaml](.pre-commit-config.yaml) runs whitespace,
  YAML/TOML, merge-conflict, large-file and secret checks, ruff, `uv-lock`, and
  the agent-doc check.
