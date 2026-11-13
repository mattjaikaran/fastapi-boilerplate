# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `AGENTS.md` as the single source of agent instructions, with
  `scripts/check_agent_docs.py` (`make agent-docs`) in CI and pre-commit to fail
  when the file is missing, a relative link does not resolve, `CLAUDE.md` holds
  prose, or a skill lacks `name`/`description` frontmatter.

### Changed

- `AGENTS.md` keeps only backend facts; global rules move to the root file. Its
  commands are `just` recipes, defined in a new `justfile` that delegates to the
  `Makefile` targets of the same name.

## [0.1.0] - 2026-11-08

First tagged release.

### Added

- FastAPI, PostgreSQL, Redis, and Celery boilerplate with Docker Compose.
- OAuth2, organizations, webhooks, and billing modules.
- Notifications, audit logs, feature flags, API keys, background jobs, and search.
- Admin, AI service, and rate limiting.
- Base service, enhanced todos, magic link login, security middleware, seed data, and factories.
- WebSocket support, a module generator, subscription status, and load tests.
- Response envelope, WebAuthn passkeys, and Redis rate limiting.
- Path-scoped rate limits, the `X-RateLimit-Reset` header, a passkey list endpoint, and production guards.
- OpenAPI export.
- Architecture, authentication, and deployment documentation with diagrams.
- Agents package with Pydantic AI and LangGraph configuration, plus AI documentation.
- Optional RabbitMQ, pgvector, and Neo4j services.
- Django Ninja HTTP client integration.
- Local SeaweedFS (`s3`) and `s3-init` Compose services under the `storage` profile, with `make up-storage`, the `AWS_S3_ENDPOINT_URL` variable, and the `DOCKER_S3_ENDPOINT_URL` variable for containers.
- `scripts/create_superuser.py` and `make create-superuser EMAIL=... [PASSWORD=...]` to create or promote a superuser. The make target passes the values as environment variables, so the password stays off the command line (`PASSWORD=` still lands in your shell history). The script reads `.env` through the app settings, refuses the default password `changeme` when `APP_ENV=production`, and exits with an error instead of prompting when no terminal is available.
- `.pre-commit-config.yaml`, with `make pre-commit-install` and `make pre-commit`.
- `0000_baseline` migration, so `alembic upgrade head` works on an empty database, and `0005_align_indexes_with_models`, so `alembic check` reports no differences.
- Application version read from `pyproject.toml` through `importlib.metadata`. The `APP_VERSION` environment variable still overrides it.
- Release tooling: this changelog, `make version`, `make bump-patch`, `make bump-minor`, `make bump-major`, `make release`, the tag-triggered `release.yml` workflow, and `docs/RELEASING.md`.
- Documentation: `docs/SERVICES.md` (service reference) and `docs/DEVELOPMENT.md` (setup, migrations, tests), and a versioning section in the README.

### Changed

- Move the default API port to 8100.
- Move the message queue settings after the Stripe settings.
- Split the README architecture diagram into its own document.
- Run diff-only CI jobs on self-hosted runners.
- Run pull request CI for any base branch.
- Replace `python-jose` with PyJWT for token signing and verification, and replace `passlib` with direct `bcrypt` calls. Remove the `bcrypt<5` pin. Passwords longer than 72 bytes are still truncated explicitly, so existing hashes keep verifying.
- Replace `redis[asyncio]` with `redis`, which includes the asyncio client.
- Move the dev dependencies from `[tool.uv] dev-dependencies` to the `[dependency-groups] dev` table, and add `pre-commit` to the group. Upgrade `uv.lock`.
- Replace FastAPI `on_event` startup and shutdown handlers with a lifespan context manager.
- Pin the uv image in the `Dockerfile` to 0.13.7.
- Update the CI actions to `actions/checkout` v7, `dorny/paths-filter` v4, and `astral-sh/setup-uv` v10.3.3.
- Rewrite `scripts/setup.sh` and `scripts/doctor.sh`. Setup now generates `SECRET_KEY` and `JWT_SECRET_KEY` when it creates `.env`.
- Remove `replicas: 2` from the `api` service in `docker-compose.prod.yml`. The fixed host port prevents scaling with Compose. Scale behind a reverse proxy or an orchestrator.
- Replace `ORJSONResponse` (deprecated in FastAPI 0.162) with FastAPI's default JSON serialization and `JSONResponse` in the health and error handlers. The response bodies do not change.
- Replace MinIO with SeaweedFS in the `storage` Compose profile, because MinIO stopped publishing community Docker images. The `s3` and `s3-init` services use pinned `chrislusf/seaweedfs` and `amazon/aws-cli` tags, and bind the S3 port to `127.0.0.1`. The `MINIO_*` variables are replaced by `S3_PORT`, and the `s3` service uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
- Update `docs/openapi.json` to include the passkey list endpoint.
- Correct the README: API reference routes, project layout, quick start, tech stack, and services. Replace a reference to a missing `API_KEYS.md` in `docs/INTEGRATIONS.md`.

### Fixed

- Reject passwords that contain NUL characters with a 422 response. bcrypt raised an error that returned a 500 response.
- Tests no longer run against the dev database. They use `TEST_DATABASE_URL` (default: `DATABASE_URL` database name plus `_test`) and refuse any database name that does not end with `_test`.
- Allow 10 seconds of clock skew when the API validates JWT `iat`, `nbf`, and `exp` claims, so tokens work across replicas with small clock differences.
- Make the release workflow fail unless the tagged commit is on `main`.
- Restore the CI model base, lockfile, and checks.
- Fix stale paths and make targets in the documentation.
- Fix rejected documentation citations and document links.
- Drop `py-webauthn`, which shadows `webauthn`.
- Keep the lint baseline for the graph service.
- Default missing LangGraph state keys.
- Lock the agents extra and LangGraph dependencies.
- Fix `alembic upgrade head` on an empty database, which failed because no migration created the base tables.
- Fix the `test-watch` target (uses `watchfiles`), the `deps-audit` target (uses `uv tool run pip-audit`), and the `build-prod` target.
- Stop recommending `scripts/seed_data.py` in the production checklist in `docs/DEPLOYMENT.md`. Use `scripts/create_superuser.py` instead.
- Remove the obsolete `ANN101` and `ANN102` Ruff ignores from `pyproject.toml`.

### Security

- Replace `python-jose`, which had advisory PYSEC-2026-4298 and pulled in `ecdsa` (advisory PYSEC-2026-1325), with PyJWT.
- Replace the unmaintained `passlib` with direct `bcrypt` calls.

[Unreleased]: https://github.com/mattjaikaran/fastapi-boilerplate/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mattjaikaran/fastapi-boilerplate/releases/tag/v0.1.0
