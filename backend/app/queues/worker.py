import asyncio
import json
import logging
import uuid
from typing import Any
import aio_pika
from sqlalchemy.ext.asyncio import AsyncSession

import app.auth.models
import app.organizations.models
import app.investigations.models
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.ingest.services import IngestService
from app.integrations.models import Integration
from sqlalchemy import select
from app.queues.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.queues.rabbitmq import RabbitMQManager, QUEUE_INGEST, rabbitmq_manager

logger = logging.getLogger(__name__)


class IngestEventWorker:
    """
    Asynchronous RabbitMQ Worker Consumer.
    
    Consumes raw telemetry events from `oip.events.ingest`, enforces CircuitBreaker
    resilience, executes signal correlation, and handles exponential backoff retries & DLQ.
    """

    def __init__(
        self,
        manager: RabbitMQManager = rabbitmq_manager,
        circuit_breaker: CircuitBreaker | None = None
    ):
        self.manager = manager
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            reset_timeout=settings.CIRCUIT_BREAKER_RESET_TIMEOUT,
        )
        self.is_running = False

    async def process_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        """Processes an incoming AMQP message with error handling, retries, and DLQ routing."""
        async with message.process(requeue=False, ignore_processed=True):
            try:
                body_str = message.body.decode("utf-8")
                envelope: dict[str, Any] = json.loads(body_str)
            except Exception as parse_err:
                logger.error(f"Failed to parse message JSON: {parse_err}. Routing to DLQ.")
                await self.manager.publish_to_dlq(
                    {"raw_body": message.body.decode("utf-8", errors="ignore")},
                    error_reason=f"JSON Parse Error: {parse_err}"
                )
                return

            event_id = envelope.get("event_id", "unknown")
            platform = envelope.get("platform", "unknown")
            payload = envelope.get("payload", {})
            org_id_str = envelope.get("organization_id")
            retry_count = envelope.get("retry_count", 0)

            # 1. Evaluate Circuit Breaker status
            if not self.circuit_breaker.allow_request():
                logger.warning(
                    f"⚠️ CircuitBreaker is OPEN. Deferring message {event_id} ({platform}) "
                    f"to retry queue with 10s delay."
                )
                await self.manager.requeue_with_backoff(envelope, retry_count, backoff_ms=10000)
                return

            # 2. Process Telemetry Ingestion in database session
            logger.info(f"Processing event {event_id} ({platform}) [Attempt #{retry_count + 1}]...")
            try:
                organization_id = uuid.UUID(org_id_str) if org_id_str else None
                mongo_db = get_mongo_db()
                
                async with AsyncSessionLocal() as db:
                    stmt = select(Integration).where(
                        Integration.platform == platform,
                        Integration.status == "active"
                    )
                    if organization_id:
                        stmt = stmt.where(Integration.organization_id == organization_id)
                    res = await db.execute(stmt)
                    integration = res.scalars().first()
                    
                    if not integration:
                        raise ValueError(f"No active integration found for platform '{platform}'")

                    await IngestService.correlate_and_process(db, mongo_db, integration, payload)
                
                # Successful execution -> record circuit success
                self.circuit_breaker.record_success()
                logger.info(f"✅ Event {event_id} ({platform}) processed successfully.")

            except ValueError as val_err:
                logger.warning(f"⚠️ Non-retryable integration error for event {event_id} ({platform}): {val_err}. Routing to DLQ.")
                await self.manager.publish_to_dlq(
                    envelope,
                    error_reason=f"Integration Validation Error: {val_err}"
                )
            except Exception as proc_err:
                logger.error(f"❌ Error processing event {event_id} ({platform}): {proc_err}")
                self.circuit_breaker.record_failure()

                # Calculate exponential backoff: initial_ms * 2^retry_count
                backoff_ms = settings.QUEUE_INITIAL_BACKOFF_MS * (2 ** retry_count)

                if retry_count < settings.QUEUE_MAX_RETRIES:
                    await self.manager.requeue_with_backoff(
                        envelope,
                        retry_count=retry_count + 1,
                        backoff_ms=backoff_ms
                    )
                else:
                    await self.manager.publish_to_dlq(
                        envelope,
                        error_reason=f"Max Retries ({settings.QUEUE_MAX_RETRIES}) Exceeded: {proc_err}"
                    )

    async def start_consumer(self):
        """Starts listening for messages on the ingest queue."""
        await self.manager.connect()
        if not self.manager.channel:
            raise RuntimeError("RabbitMQ channel is not initialized.")

        queue = await self.manager.channel.get_queue(QUEUE_INGEST)
        self.is_running = True
        logger.info(f"🚀 IngestEventWorker consumer started listening on '{QUEUE_INGEST}'...")

        await queue.consume(self.process_message)


# Global Singleton Worker instance
worker_instance = IngestEventWorker()
