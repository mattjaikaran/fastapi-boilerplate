"""Build the Pydantic AI model from the agent settings and provider keys."""

from pydantic_ai.models import Model
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

ANTHROPIC_PREFIXES = ("claude",)
OPENAI_PREFIXES = ("gpt", "o1", "o3", "o4", "o5")


def _require_key(key: str, provider: str, model_name: str) -> str:
    if not key:
        raise RuntimeError(
            f"AGENT_DEFAULT_MODEL={model_name!r} needs {provider}. "
            f"Set {provider} in .env or change AGENT_DEFAULT_MODEL."
        )
    return key


def build_model(model_name: str | None = None) -> Model:
    """Return the configured model, or raise if its provider has no API key.

    ``AGENT_DEFAULT_MODEL`` selects the provider by name: ``claude*`` uses
    Anthropic and ``gpt*``/``o1``-``o5`` use OpenAI. Settings load on first call
    so importing agent modules does not require environment configuration.
    """
    from app.config.settings import settings

    name = (model_name or settings.AGENT_DEFAULT_MODEL).strip()
    lowered = name.lower()

    if lowered.startswith(ANTHROPIC_PREFIXES):
        key = _require_key(settings.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY", name)
        return AnthropicModel(name, provider=AnthropicProvider(api_key=key))

    if lowered.startswith(OPENAI_PREFIXES):
        key = _require_key(settings.OPENAI_API_KEY, "OPENAI_API_KEY", name)
        return OpenAIChatModel(name, provider=OpenAIProvider(api_key=key))

    raise ValueError(
        f"Unsupported AGENT_DEFAULT_MODEL {name!r}: use a claude*, gpt* or o1-o5* "
        "model name."
    )
