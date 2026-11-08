from __future__ import annotations

from typing import TYPE_CHECKING, Any

from neo4j import AsyncGraphDatabase, Query

from app.config.settings import settings

if TYPE_CHECKING:
    from neo4j import AsyncDriver


class Neo4jClient:
    """Lazy async Neo4j client.

    The driver is created on first use, so the application imports and starts
    normally when the optional graph service is not running.
    """

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def connect(self) -> None:
        """Verify connectivity, raising if Neo4j is unreachable."""
        await self.driver.verify_connectivity()

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None

    async def run(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run a Cypher query and return the records as dictionaries."""
        async with self.driver.session() as session:
            result = await session.run(Query(query), params)
            return [record.data() async for record in result]


_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
