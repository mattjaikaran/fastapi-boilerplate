from typing import Any

import redis.asyncio as aioredis

from app.config.settings import settings

_redis_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


class CacheService:
    def __init__(self) -> None:
        self.redis = get_redis()

    async def get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int | None = None) -> None:
        if expire:
            await self.redis.setex(key, expire, value)
        else:
            await self.redis.set(key, value)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(key))

    async def increment(self, key: str, expire: int | None = None) -> int:
        count = await self.redis.incr(key)
        if expire and count == 1:
            await self.redis.expire(key, expire)
        return count

    async def get_json(self, key: str) -> Any:
        import orjson

        value = await self.redis.get(key)
        if value is None:
            return None
        return orjson.loads(value)

    async def set_json(self, key: str, value: Any, expire: int | None = None) -> None:
        import orjson

        serialized = orjson.dumps(value).decode()
        await self.set(key, serialized, expire=expire)

    async def close(self) -> None:
        await self.redis.aclose()


def get_cache_service() -> CacheService:
    return CacheService()
