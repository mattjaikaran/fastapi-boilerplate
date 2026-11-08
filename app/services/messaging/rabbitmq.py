"""RabbitMQ publish/consume helpers.

The connection is opened on first use, so the API starts and runs without a
broker. The ``mq`` extra (``uv sync --extra mq``) is only imported inside the
helpers for the same reason.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import orjson
import structlog

from app.config.settings import settings

if TYPE_CHECKING:
    from aio_pika.abc import (
        AbstractChannel,
        AbstractExchange,
        AbstractIncomingMessage,
        AbstractRobustConnection,
    )

logger = structlog.get_logger()

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None
_exchange: AbstractExchange | None = None
_lock = asyncio.Lock()


async def _get_channel() -> tuple[AbstractChannel, AbstractExchange]:
    """Return an open channel plus the durable topic exchange.

    Reconnects and redeclares the exchange when the previous channel closed.
    """
    global _connection, _channel, _exchange

    from aio_pika import ExchangeType, connect_robust

    async with _lock:
        if _channel is None or _channel.is_closed:
            if _connection is None or _connection.is_closed:
                _connection = await connect_robust(settings.RABBITMQ_URL)
            _channel = await _connection.channel()
            _exchange = await _channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                ExchangeType.TOPIC,
                durable=True,
            )
        if _exchange is None:
            raise RuntimeError("RabbitMQ exchange is not available")
        return _channel, _exchange


async def publish(routing_key: str, payload: dict[str, Any]) -> None:
    """Publish ``payload`` as a persistent JSON message to ``routing_key``."""
    from aio_pika import DeliveryMode, Message

    _, exchange = await _get_channel()
    await exchange.publish(
        Message(
            body=orjson.dumps(payload),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        ),
        routing_key=routing_key,
    )
    logger.debug("rabbitmq_published", routing_key=routing_key)


async def consume(queue: str, routing_key: str, handler: MessageHandler) -> None:
    """Bind a durable ``queue`` to ``routing_key`` and start consuming.

    Returns once the consumer is registered; the handler runs in the asyncio
    loop, so keep the process alive. Failed messages are rejected and requeued.
    """
    channel, exchange = await _get_channel()
    declared = await channel.declare_queue(queue, durable=True)
    await declared.bind(exchange, routing_key=routing_key)

    async def _on_message(message: AbstractIncomingMessage) -> None:
        try:
            await handler(orjson.loads(message.body))
        except Exception:
            logger.exception(
                "rabbitmq_handler_failed",
                queue=queue,
                routing_key=routing_key,
            )
            await message.reject(requeue=True)
        else:
            await message.ack()

    await declared.consume(_on_message)
    logger.info("rabbitmq_consuming", queue=queue, routing_key=routing_key)
