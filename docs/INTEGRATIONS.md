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
