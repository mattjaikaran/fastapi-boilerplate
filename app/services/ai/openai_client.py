"""OpenAI client — drop in OPENAI_API_KEY and it works."""
from typing import Any

import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class OpenAIService:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            if not settings.OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not configured")
            from openai import OpenAI

            cls._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return cls._client

    @classmethod
    def chat(
        cls,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        client = cls.get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    @classmethod
    async def chat_async(
        cls,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    @classmethod
    def embed(cls, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        client = cls.get_client()
        response = client.embeddings.create(input=texts, model=model)
        return [e.embedding for e in response.data]

    @classmethod
    async def embed_async(
        cls, texts: list[str], model: str = "text-embedding-3-small"
    ) -> list[list[float]]:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(input=texts, model=model)
        return [e.embedding for e in response.data]

    @classmethod
    def stream(
        cls,
        messages: list[dict[str, str]],
        model: str = "gpt-4o",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Yields text chunks from a streaming response."""
        client = cls.get_client()
        with client.chat.completions.stream(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
        ) as stream:
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
