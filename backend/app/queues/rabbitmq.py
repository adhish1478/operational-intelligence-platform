import json
import logging
import uuid
from datetime import datetime
from typing import Any
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode

from app.core.config import settings

logger = logging.getLogger(__name__)

# AMQP Topology Constants
EXCHANGE_MAIN = "oip.events.exchange"
EXCHANGE_RETRY = "oip.events.retry.exchange"

QUEUE_INGEST = "oip.events.ingest"
QUEUE_RETRY = "oip.events.retry"
QUEUE_DLQ = "oip.events.dlq"

ROUTING_INGEST_PREFIX = "event.ingest."
ROUTING_RETRY = "event.retry"
ROUTING_DLQ = "event.dlq"


class RabbitMQManager:
    """
    Asynchronous RabbitMQ Client & Topology Manager.
    
    Manages connection pools, exchange/queue declarations, message publishing,
    exponential backoff dead-lettering, and Dead Letter Queue (DLQ) routing.
    """

    def __init__(self, amqp_url: str = settings.RABBITMQ_URL):
        self.amqp_url = amqp_url
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None
        self.main_exchange: aio_pika.RobustExchange | None = None
        self.retry_exchange: aio_pika.RobustExchange | None = None

    async def connect(self):
        """Establishes robust AMQP connection and declares exchanges and queue topology."""
        if self.connection and not self.connection.is_closed:
            return

        logger.info(f"Connecting to RabbitMQ cluster at {self.amqp_url}...")
        try:
            self.connection = await aio_pika.connect_robust(self.amqp_url, timeout=10.0)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)

            # 1. Declare Topic Exchanges
            self.main_exchange = await self.channel.declare_exchange(
                EXCHANGE_MAIN, type=ExchangeType.TOPIC, durable=True
            )
            self.retry_exchange = await self.channel.declare_exchange(
                EXCHANGE_RETRY, type=ExchangeType.TOPIC, durable=True
            )

            # 2. Declare Ingest Queue (bound to main exchange)
            ingest_queue = await self.channel.declare_queue(
                QUEUE_INGEST,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": EXCHANGE_MAIN,
                    "x-dead-letter-routing-key": ROUTING_DLQ,
                }
            )
            await ingest_queue.bind(self.main_exchange, routing_key="event.ingest.#")

            # 3. Declare Retry Queue (with Dead-Letter routing back to main exchange upon TTL expiration)
            retry_queue = await self.channel.declare_queue(
                QUEUE_RETRY,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": EXCHANGE_MAIN,
                    "x-dead-letter-routing-key": "event.ingest.retry",
                }
            )
            await retry_queue.bind(self.retry_exchange, routing_key="event.retry.#")

            # 4. Declare Dead Letter Queue (DLQ for poison messages)
            dlq_queue = await self.channel.declare_queue(QUEUE_DLQ, durable=True)
            await dlq_queue.bind(self.main_exchange, routing_key=ROUTING_DLQ)

            logger.info("✅ RabbitMQ Topology declared successfully (Main, Retry with TTL, DLQ).")
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ connection: {e}")
            raise

    async def close(self):
        """Closes channel and connection gracefully."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed.")

    async def publish_event(
        self,
        platform: str,
        payload: dict[str, Any],
        organization_id: str,
        correlation_id: str | None = None
    ) -> str:
        """
        Publishes a raw telemetry event to the RabbitMQ main exchange.
        Returns the generated event UUID.
        """
        if not self.main_exchange:
            await self.connect()

        event_id = str(uuid.uuid4())
        routing_key = f"{ROUTING_INGEST_PREFIX}{platform}"

        envelope = {
            "event_id": event_id,
            "platform": platform,
            "payload": payload,
            "organization_id": str(organization_id),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": 0,
        }

        body = json.dumps(envelope).encode("utf-8")
        message = Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event_id,
            headers={"x-retry-count": 0, "x-platform": platform}
        )

        await self.main_exchange.publish(message, routing_key=routing_key)
        logger.info(f"Published raw event {event_id} ({platform}) to RabbitMQ routing key '{routing_key}'.")
        return event_id

    async def requeue_with_backoff(self, envelope: dict[str, Any], retry_count: int, backoff_ms: int):
        """
        Publishes a failed message to the Retry Exchange with a message TTL expiration.
        When TTL expires, RabbitMQ automatically routes it back to the Ingest Queue.
        """
        if not self.retry_exchange:
            await self.connect()

        envelope["retry_count"] = retry_count
        envelope["last_retry_at"] = datetime.utcnow().isoformat()
        body = json.dumps(envelope).encode("utf-8")

        message = Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            expiration=str(backoff_ms),
            headers={
                "x-retry-count": retry_count,
                "x-backoff-ms": backoff_ms,
                "x-platform": envelope.get("platform", "unknown"),
            }
        )

        routing_key = f"{ROUTING_RETRY}.{envelope.get('platform', 'unknown')}"
        await self.retry_exchange.publish(message, routing_key=routing_key)
        logger.warning(
            f"Requeued event {envelope.get('event_id')} for retry #{retry_count} "
            f"with exponential backoff TTL {backoff_ms}ms."
        )

    async def publish_to_dlq(self, envelope: dict[str, Any], error_reason: str):
        """Publishes an unrecoverable poison message to the Dead Letter Queue (DLQ)."""
        if not self.main_exchange:
            await self.connect()

        envelope["failed_at"] = datetime.utcnow().isoformat()
        envelope["error_reason"] = error_reason
        body = json.dumps(envelope).encode("utf-8")

        message = Message(
            body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            headers={
                "x-dead-letter": "true",
                "x-error-reason": error_reason[:255],
                "x-platform": envelope.get("platform", "unknown"),
            }
        )

        await self.main_exchange.publish(message, routing_key=ROUTING_DLQ)
        logger.error(
            f"☠️ Poison message {envelope.get('event_id')} exceeded max retries. "
            f"Routed to Dead Letter Queue (DLQ) '{QUEUE_DLQ}'. Reason: {error_reason}"
        )


# Global Singleton Manager instance
rabbitmq_manager = RabbitMQManager()
