# Services reference

This page lists every service in `docker-compose.yml`. Core services start with `make up`. Optional services start only when you enable their Compose profile.

For deployment with `docker-compose.prod.yml`, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Core services

These services have no profile. `make up` starts them.

| Service | Purpose | Host port (override variable) | Env vars |
|---|---|---|---|
| `db` | PostgreSQL 17 primary database | 5432 (`POSTGRES_PORT`) | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL` |
| `redis` | Cache, OTP, lockout counters, Celery broker and result backend | 6379 (`REDIS_PORT`) | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `api` | FastAPI app (development image, hot reload) | 8100 (`APP_PORT`) | See [`.env.example`](../.env.example) |

Inside the Compose network, the `api`, `worker`, and `beat` services override `DATABASE_URL`, `REDIS_URL`, and the Celery URLs to use the service host names (`db`, `redis`).

---

## Optional services

Each optional service has one Compose profile and one Make target. Each Make target starts the core services plus that profile.

| Service | Purpose | Compose profile | Make target | Host ports | Env vars | Details |
|---|---|---|---|---|---|---|
| `pgvector` | PostgreSQL 17 with the pgvector extension for embeddings | `vector` | `make up-vector` | 5433 (`VECTOR_POSTGRES_PORT`) | `VECTOR_DATABASE_URL`, `VECTOR_POSTGRES_PORT`, `EMBEDDING_DIMENSIONS` | [VECTOR.md](VECTOR.md) |
| `rabbitmq` | Message broker for events shared with other services | `mq` | `make up-mq` | 5672 AMQP (`RABBITMQ_PORT`), 15672 management UI (`RABBITMQ_MANAGEMENT_PORT`) | `RABBITMQ_URL`, `RABBITMQ_EXCHANGE` | [INTEGRATIONS.md](INTEGRATIONS.md#rabbitmq) |
| `worker` | Celery worker for the `default`, `email`, `notifications`, and `ml` queues | `celery` | `make up-celery` | None | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER` | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `beat` | Celery beat scheduler for periodic tasks | `celery` | `make up-celery` | None | `CELERY_BROKER_URL` | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `flower` | Celery monitoring UI | `monitoring` | `make up-monitoring` | 5555 | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | [DEPLOYMENT.md](DEPLOYMENT.md) |
| `neo4j` | Neo4j 5 Community graph database | `graph` | `make up-graph` | 7474 Browser, 7687 Bolt | `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | [GRAPH.md](GRAPH.md) |
| `s3` | SeaweedFS S3-compatible object storage for local upload tests | `storage` | `make up-storage` | 8333 S3 API (`S3_PORT`) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_ENDPOINT_URL`, `DOCKER_S3_ENDPOINT_URL` | [S3 storage setup](#seaweedfs-s3-compatible-storage) |
| `s3-init` | One-shot job that creates the `AWS_S3_BUCKET` bucket in SeaweedFS | `storage` | `make up-storage` | None | `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | [S3 storage setup](#seaweedfs-s3-compatible-storage) |

`make up-monitoring` enables both the `celery` and `monitoring` profiles, so it also starts `worker` and `beat`.

### Combine profiles

Each Make target enables one profile (`up-monitoring` enables two). To run more optional services at once, pass several `--profile` flags:

```bash
docker compose --profile celery --profile graph --profile storage up -d
```

### Install optional Python packages

Some services need an optional dependency group in `pyproject.toml`. The default `uv sync` does not install them.

| Service | Extra | Command |
|---|---|---|
| `rabbitmq` | `mq` | `uv sync --extra mq` |
| `pgvector` | `vector` | `uv sync --extra vector` |
| `neo4j` | `graph` | `uv sync --extra graph` |
| Agents (see [AI_AGENTS.md](AI_AGENTS.md)) | `agents` | `uv sync --extra agents` |

`make install-dev` runs `uv sync --all-extras`, which installs every extra.

---

## SeaweedFS (S3-compatible storage)

Use SeaweedFS to test the `s3` storage driver without an AWS account. MinIO stopped publishing community Docker images, so the `storage` profile uses SeaweedFS.

1. Start the service:

   ```bash
   make up-storage
   ```

   The `s3-init` job creates the bucket named in `AWS_S3_BUCKET`. The Compose default is `app-uploads`.

2. Set these values in `.env`:

   ```bash
   STORAGE_DRIVER=s3
   AWS_ACCESS_KEY_ID=s3devkey
   AWS_SECRET_ACCESS_KEY=s3devsecret
   AWS_S3_BUCKET=app-uploads
   AWS_S3_ENDPOINT_URL=http://localhost:8333
   ```

   The `s3` service uses `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as its admin credentials. When you do not set them, Compose uses `s3devkey` and `s3devsecret`.

   The `api` and `worker` containers cannot reach SeaweedFS at `localhost`. Set `DOCKER_S3_ENDPOINT_URL=http://s3:8333` so the containers use the Compose host name. When `DOCKER_S3_ENDPOINT_URL` is empty, the containers use `AWS_S3_ENDPOINT_URL`.

Change the credentials before you expose the port outside your machine.

---

## Stop services

```bash
make down           # stop all services, keep data volumes
make down-volumes   # stop all services and delete data volumes (DESTRUCTIVE)
```
