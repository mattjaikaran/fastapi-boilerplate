# Integrations

Cross-service integrations that are optional to the core boilerplate.

---

## RabbitMQ

Optional message broker for exchanging events with other services
(for example `django-ninja-boilerplate`). It is not needed by the API, Celery
or any other default service.

### Start the broker

RabbitMQ lives in the `mq` compose profile, so it is only started when asked
for:

```bash
docker compose --profile mq up -d rabbitmq
```

| Port | Usage |
|---|---|
| 5672 | AMQP |
| 15672 | Management UI — <http://localhost:15672> (guest / guest) |

The image is `rabbitmq:4-management-alpine`, with a `rabbitmq-diagnostics -q ping`
health check and a `rabbitmq_data` volume.

### Install the client

`aio-pika` is an optional extra, so the default install does not pull it in:

```bash
uv sync --extra mq
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | AMQP connection URL |
| `RABBITMQ_EXCHANGE` | `platform.events` | Durable topic exchange shared with other services |

Inside the compose network, rabbitmq is reachable as
`amqp://guest:guest@rabbitmq:5672/`.

### Publish and consume

The helpers live in `app/services/messaging` and connect lazily on first use,
so the app starts and serves traffic with no broker running. Only when a
publish or consume is attempted is a connection opened.

```python
from app.services.messaging import publish

await publish(
    "fastapi.todo.created",
    {"id": str(todo.id), "title": todo.title},
)
```

```python
from app.services.messaging import consume

async def handle_todo_created(payload: dict) -> None:
    ...

await consume("fastapi.todo-events", "fastapi.todo.*", handle_todo_created)
# Returns once the consumer is registered — keep the event loop running.
```

Messages are JSON bodies, published as persistent messages to a durable topic
exchange. Consumers declare a durable queue, bind it to the routing key, and
ack on success or reject with requeue when the handler raises.

### Routing-key convention

Routing keys are dot-separated, lowercase and follow
`<source>.<entity>.<event>`:

| Segment | Example | Meaning |
|---|---|---|
| `source` | `fastapi`, `django` | Service that emitted the event |
| `entity` | `todo`, `user` | Domain object that changed |
| `event` | `created`, `updated`, `deleted` | What happened |

Examples: `fastapi.todo.created`, `django.user.updated`,
`fastapi.api_key.revoked`. Consumers bind patterns such as `django.user.*` or
`*.*.deleted`.

### Notes

- A failed handler is logged (`rabbitmq_handler_failed`) and the message is
  requeued, so handlers should be idempotent.
- Celery keeps using Redis; RabbitMQ does not replace the task queue.

---

## Django Ninja Client

`app/services/integrations/ninja_client.py` wraps an `httpx.AsyncClient` for the
Django service. It sends the API key on every request, applies a timeout, and
raises a typed error for non-2xx responses.

Django Ninja serves its API under `/api/` with no version prefix and
authenticates machine-to-machine callers with the `X-API-Key` header.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NINJA_BASE_URL` | `http://localhost:8000/api` | Base URL of the Django API, including `/api` |
| `NINJA_API_KEY` | empty | Raw API key from django-ninja-boilerplate (`{prefix}.{secret}`) |
| `NINJA_TIMEOUT_SECONDS` | `10` | Per-request timeout in seconds |

Add them to `.env` (see [`.env.example`](../.env.example)). The Django service
listens on port 8000 by default; this app moves to 8100, so the default base URL
does not collide with the local dev server.

### Create an API key

Keys are created in the Django app with a JWT-authenticated request and the raw
value is returned once:

```bash
curl -X POST http://localhost:8000/api/api-keys/ \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "fastapi-boilerplate", "scopes": ["read:todos"], "expires_in_days": 90}'
```

Copy the `key` field into `NINJA_API_KEY`. The Django service owns the key
lifecycle (scopes, expiry, and revocation). This repository does not include
documentation for it; use the documentation in the django-ninja-boilerplate
repository. Store the key in `.env` and never commit it.

### Use it in a route

`get_ninja_client` is a FastAPI dependency. The client is created on first use
and reused for the life of the process:

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from app.services.integrations.ninja_client import NinjaClient, get_ninja_client

router = APIRouter()


@router.get("/todos")
async def list_todos(
    client: Annotated[NinjaClient, Depends(get_ninja_client)],
) -> object:
    return await client.get("/todos/")
```

### Direct use

Construct a client when you need a different base URL or want to scope its
lifetime:

```python
from app.services.integrations.ninja_client import NinjaClient

async with NinjaClient(base_url="http://django:8000/api") as client:
    todo = await client.post("/todos/", json={"title": "Ship it"})
```

### Methods

| Method | Behavior |
|---|---|
| `get(path, *, params=None)` | GET and decode the JSON response |
| `post(path, *, json=None)` | POST a JSON body and decode the JSON response |
| `health()` | `True` when `GET /health/` succeeds, `False` on any error |
| `aclose()` | Close the connection pool |

Paths are relative to `NINJA_BASE_URL`. The Django health endpoints live at
`/api/health/`, `/api/health/liveness` and `/api/health/readiness`.

### Errors

Any non-2xx response raises `NinjaClientError` with the upstream `status_code`
and the response body in `detail`. Transport failures (DNS, connect, timeout)
raise the same error with `status_code=None`.

```python
from app.services.integrations.ninja_client import NinjaClientError

try:
    await client.get("/todos/")
except NinjaClientError as exc:
    logger.warning("ninja_call_failed", status=exc.status_code, detail=exc.detail)
```

`health()` is the exception: it swallows `NinjaClientError` and returns `False`,
so it can back a readiness probe.

### Lifecycle

The module holds one shared client behind `get_ninja_client()`. `app/main.py`
calls `close_ninja_client()` in the shutdown hook, which closes the pool and
clears the reference. Nothing connects to Django at import or startup time.

### Testing

Mock the HTTP layer with `respx` (already in the dev extra). Point the client at
a fake base URL and assert on the recorded request:

```python
import httpx
import respx

from app.services.integrations.ninja_client import NinjaClient

with respx.mock(base_url="http://ninja.test/api") as router:
    router.get("/todos/").mock(return_value=httpx.Response(200, json=[]))

    async with NinjaClient(base_url="http://ninja.test/api", api_key="k") as client:
        assert await client.get("/todos/") == []
```

See `tests/integration/test_ninja_client.py` for the smoke test.
