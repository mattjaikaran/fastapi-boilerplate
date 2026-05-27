"""WebSocket connection manager — per-user connection registry."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    import uuid

    from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Thread-safe registry mapping user_id → set of live WebSocket connections.

    Each user can hold multiple simultaneous connections (multiple tabs / devices).
    Messages are broadcast to all of them; stale connections are reaped on send failure.
    """

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: uuid.UUID, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[user_id].add(ws)
        conn_count = len(self._connections[user_id])
        logger.info("ws.connected", user_id=str(user_id), total=conn_count)

    async def disconnect(self, user_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[user_id].discard(ws)
            if not self._connections[user_id]:
                del self._connections[user_id]
        logger.info("ws.disconnected", user_id=str(user_id))

    async def send(self, user_id: uuid.UUID, payload: dict[str, Any]) -> int:
        """Push payload to every connection for user_id. Returns delivery count."""
        sockets = list(self._connections.get(user_id, set()))
        if not sockets:
            return 0

        dead: list[WebSocket] = []
        delivered = 0
        for ws in sockets:
            try:
                await ws.send_json(payload)
                delivered += 1
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[user_id].discard(ws)
                if not self._connections[user_id]:
                    self._connections.pop(user_id, None)

        return delivered

    async def broadcast(self, payload: dict[str, Any]) -> int:
        """Push payload to ALL connected users. Returns total delivery count."""
        user_ids = list(self._connections.keys())
        total = 0
        for uid in user_ids:
            total += await self.send(uid, payload)
        return total

    def is_online(self, user_id: uuid.UUID) -> bool:
        return bool(self._connections.get(user_id))

    @property
    def online_count(self) -> int:
        return len(self._connections)


# Application-level singleton shared across the process
ws_manager = ConnectionManager()
