"""Agents: multi-step AI workloads built on the existing AI clients.

Layout rules:

- Agents call the clients in ``app/services/ai`` (``AnthropicService``,
  ``OpenAIService``); they never instantiate SDK clients themselves.
- Routers call agents; agents never import from ``app/api``.
- Agents never touch the database directly. Persistence goes through a
  service in ``app/services`` or a task in ``app/workers/tasks``.

See ``docs/AI_AGENTS.md`` for settings and how to add an agent.
"""
