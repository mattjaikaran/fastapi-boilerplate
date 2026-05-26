"""Anthropic Claude client — drop in ANTHROPIC_API_KEY and it works."""
from typing import Any, AsyncIterator, TypeVar

import structlog
from pydantic import BaseModel

from app.config.settings import settings

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class AnthropicService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            if not settings.ANTHROPIC_API_KEY:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")
            from anthropic import Anthropic

            cls._client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        return cls._client

    @classmethod
    def chat(
        cls,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        client = cls.get_client()
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            params["system"] = system
        params.update(kwargs)

        response = client.messages.create(**params)
        return response.content[0].text

    @classmethod
    async def chat_async(
        cls,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        system: str | None = None,
        **kwargs: Any,
    ) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            params["system"] = system
        params.update(kwargs)

        response = await client.messages.create(**params)
        return response.content[0].text

    @classmethod
    def stream(
        cls,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        system: str | None = None,
    ):
        """Yields text chunks from a streaming response."""
        client = cls.get_client()
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            params["system"] = system

        with client.messages.stream(**params) as stream:
            for text in stream.text_stream:
                yield text

    @classmethod
    async def stream_async(
        cls,
        messages: list[dict[str, str]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> AsyncIterator[str]:
        """Async generator yielding text chunks from a streaming response."""
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            params["system"] = system

        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text

    @classmethod
    async def structured_output(
        cls,
        messages: list[dict[str, str]],
        output_schema: type[T],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
        system: str | None = None,
    ) -> T:
        """Force structured JSON output validated against a Pydantic model.

        Uses tool_use to guarantee schema-conformant output.
        """
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        schema = output_schema.model_json_schema()
        tool = {
            "name": "structured_output",
            "description": f"Return a structured response conforming to the {output_schema.__name__} schema.",
            "input_schema": schema,
        }

        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "structured_output"},
        }
        if system:
            params["system"] = system

        response = await client.messages.create(**params)

        for block in response.content:
            if block.type == "tool_use" and block.name == "structured_output":
                return output_schema.model_validate(block.input)

        raise ValueError("Model did not return a structured tool_use block")
