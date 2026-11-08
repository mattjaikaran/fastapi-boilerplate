# AI & Agents

Where AI code lives and the rules for adding agent workloads.

---

## Layout

```
app/
├── agents/                    # agent orchestration (this package)
│   ├── __init__.py            # package rules, see docstring
│   └── pydantic_ai/           # Pydantic AI config and example agent (agents extra)
├── api/ai/                    # HTTP endpoints: chat, structured output, stream
├── services/ai/               # provider clients
│   ├── anthropic_client.py    # AnthropicService — chat, structured, stream
│   └── openai_client.py       # OpenAIService — chat, embeddings
└── workers/tasks/ml.py        # long-running inference on the `ml` queue
```

Dependency layering — one direction only:

```
router (app/api)  ->  agent (app/agents)  ->  client (app/services/ai)
```

- Agents call `AnthropicService` / `OpenAIService`; they never build SDK clients themselves.
- Routers call agents; agents never import from `app/api`.
- Agents never touch the database directly — go through a service in `app/services`, or hand the work to a Celery task.

---

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `AGENT_DEFAULT_MODEL` | `claude-sonnet-4-6` | Model used when a caller does not name one |
| `AGENT_MAX_STEPS` | `10` | Maximum reason/act iterations per run |
| `AGENT_TIMEOUT_SECONDS` | `60` | Hard wall-clock limit per run |

Read them from `app.config.settings.settings`:

```python
from app.config.settings import settings

model = settings.AGENT_DEFAULT_MODEL
for _ in range(settings.AGENT_MAX_STEPS):
    ...
```

Provider keys are shared with the existing clients: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. A missing key raises `RuntimeError` on first client use.

---

## Optional dependency group

`pyproject.toml` has an `agents` extra with the agent frameworks (Pydantic AI today, LangGraph later), so core installs stay lean:

```bash
uv sync                  # core only
uv sync --extra agents   # core + agent frameworks
```

---

## Pydantic AI

Install the extra:

```bash
uv sync --extra agents
```

The example agent in `app/agents/pydantic_ai/example_agent.py` returns a typed
`ArticleSummary` (`headline`, `summary`, `key_points`) and has one tool,
`word_stats`, that counts words and characters. `get_agent()` builds it on first
call and reuses it:

```python
import asyncio

from app.agents.pydantic_ai.example_agent import get_agent


async def main() -> None:
    result = await get_agent().run("Paste an article here.")
    print(result.output.headline)
    print(result.output.summary)
    print(result.output.key_points)


asyncio.run(main())
```

Export `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` with a matching
`AGENT_DEFAULT_MODEL`) before running it. Use `build_model("gpt-5")` from
`app/agents/pydantic_ai/config.py` to override the model for one agent.

## Adding an agent

1. Create `app/agents/<name>.py` with a class or functions that take plain inputs and return plain data.

```python
"""Summarise a thread of messages."""

from app.config.settings import settings
from app.services.ai.anthropic_client import AnthropicService


async def summarise(messages: list[dict[str, str]]) -> str:
    return await AnthropicService.chat_async(
        messages=messages,
        model=settings.AGENT_DEFAULT_MODEL,
        max_tokens=512,
    )
```

2. Enforce the limits from settings: stop after `AGENT_MAX_STEPS` iterations and abort past `AGENT_TIMEOUT_SECONDS`.
3. Expose it from a router in `app/api/<module>/` if it needs HTTP. Keep provider details out of the router.
4. Move work that takes longer than a request to Celery — see below.

---

## Background work: the `ml` queue

`app/workers/tasks/ml.py` registers tasks on the dedicated `ml` queue, routed by `task_routes` in `app/workers/celery_app.py`. Use it for inference, embeddings, and multi-step agent runs that would blow a request timeout:

```python
from app.workers.tasks.ml import run_inference

run_inference.delay(model_name="summariser", inputs={"messages": [...]})
```

Start a worker for it:

```bash
uv run celery -A app.workers.celery_app worker -Q ml
```

Results land in the Celery result backend (Redis) and can be polled through `app/api/jobs/`.

---

## Related

- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — service layer and request flow
- [FEATURE_GENERATION.md](../FEATURE_GENERATION.md) — scaffolding a new API module
