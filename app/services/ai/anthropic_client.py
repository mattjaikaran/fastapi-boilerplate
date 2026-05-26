"""Anthropic Claude client — drop in ANTHROPIC_API_KEY and it works."""
from typing import Any

import structlog

from app.config.settings import settings

logger = structlog.get_logger()


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
