# Backend recipes named in AGENTS.md. Each one runs the Makefile target of the
# same name, or the command it names. `just` lists them.

default:
    @just --list

setup:
    ./scripts/setup.sh

doctor:
    ./scripts/doctor.sh

up:
    make up

dev:
    make dev

build:
    make build

build-prod:
    make build-prod

migrate:
    make migrate

migrate-local:
    make migrate-local

migration msg:
    make migration msg="{{msg}}"

migration-check:
    uv run alembic check

seed:
    make seed

seed-local:
    make seed-local

lint:
    make lint

format-check:
    make format-check

typecheck:
    make typecheck

check:
    make check

test-unit:
    make test-unit

test-integration:
    make test-integration

test-smoke:
    make test-smoke

test-e2e:
    make test-e2e

test-ml:
    make test-ml

pre-commit-install:
    make pre-commit-install

pre-commit:
    make pre-commit

agent-docs:
    make agent-docs

generate module:
    make generate MODULE={{module}}

health:
    make health

ready:
    make ready
