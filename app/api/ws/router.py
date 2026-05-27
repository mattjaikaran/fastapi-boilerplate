"""WebSocket endpoint — real-time notification push with JWT auth."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.ws.manager import ws_manager
from app.config.database import async_session_factory
from app.core.security.jwt import decode_token

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])


async def _authenticate(token: str) -> uuid.UUID | None:
    """Decode JWT and return user_id, or None on failure."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return uuid.UUID(payload["sub"])
    except Exception:
        return None


@router.websocket("/notifications")
async def notifications_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    Real-time notification stream.

    Connect:  ws://host/api/ws/notifications?token=<access_token>

    Server pushes JSON frames:
      {"event": "notification", "data": {...notification fields...}}
      {"event": "ping"}

    Client may send:
      {"action": "ping"}   → server replies {"event": "pong"}
    """
    user_id = await _authenticate(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Verify user is active
    async with async_session_factory() as db:
        from app.api.users.service import UserService
        try:
            user = await UserService(db).get_by_id(user_id)
            if not user.is_active:
                await websocket.close(code=4003, reason="Account inactive")
                return
        except Exception:
            await websocket.close(code=4004, reason="User not found")
            return

    await ws_manager.connect(user_id, websocket)
    try:
        await websocket.send_json(
            {"event": "connected", "data": {"user_id": str(user_id)}}
        )

        while True:
            try:
                msg = await websocket.receive_json()
                if msg.get("action") == "ping":
                    await websocket.send_json({"event": "pong"})
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.warning("ws.receive_error", user_id=str(user_id), error=str(exc))
                break
    finally:
        await ws_manager.disconnect(user_id, websocket)
