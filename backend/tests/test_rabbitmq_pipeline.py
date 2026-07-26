import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.queues.circuit_breaker import CircuitBreaker, CircuitState
from app.queues.rabbitmq import RabbitMQManager
from app.queues.worker import IngestEventWorker
from app.core.config import settings


def test_circuit_breaker_state_transitions():
    """Verifies CircuitBreaker trips to OPEN after threshold and resets to HALF_OPEN after cooldown."""
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=0.2)
    
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 1. Record failures up to threshold
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 2. Third failure trips circuit to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    # 3. Wait for cooldown reset_timeout (0.2s)
    time.sleep(0.25)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 4. Successful request in HALF_OPEN resets to CLOSED
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure():
    """Verifies failure in HALF_OPEN state immediately re-trips circuit to OPEN."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=0.1)
    
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.15)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Failure during trial re-trips to OPEN
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_exponential_backoff_calculation():
    """Verifies exponential backoff delay calculation formula (initial_ms * 2^retry_count)."""
    initial_ms = settings.QUEUE_INITIAL_BACKOFF_MS  # 2000ms
    
    delays = [initial_ms * (2 ** retry) for retry in range(5)]
    assert delays == [2000, 4000, 8000, 16000, 32000]


@pytest.mark.asyncio
async def test_worker_instantiation():
    """Verifies IngestEventWorker initializes with circuit breaker and settings."""
    worker = IngestEventWorker()
    assert worker.circuit_breaker.failure_threshold == settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
    assert worker.circuit_breaker.reset_timeout == settings.CIRCUIT_BREAKER_RESET_TIMEOUT
    assert worker.is_running is False


@pytest.mark.asyncio
async def test_worker_retry_and_dlq_routing():
    """Verifies worker handles retries with exponential backoff and routes to DLQ on max retries."""
    mock_manager = MagicMock(spec=RabbitMQManager)
    mock_manager.requeue_with_backoff = AsyncMock()
    mock_manager.publish_to_dlq = AsyncMock()

    worker = IngestEventWorker(manager=mock_manager)

    # 1. Test Retry Path (retry_count < QUEUE_MAX_RETRIES)
    envelope_retry = {
        "event_id": "test-evt-1",
        "platform": "slack",
        "payload": {"text": "test error message"},
        "organization_id": "00000000-0000-0000-0000-000000000000",
        "retry_count": 1,
    }

    mock_msg = MagicMock()
    mock_msg.process = MagicMock()
    mock_msg.process.return_value.__aenter__ = AsyncMock()
    mock_msg.process.return_value.__aexit__ = AsyncMock()
    mock_msg.body = str(envelope_retry).replace("'", '"').encode("utf-8")

    with patch("app.queues.worker.IngestService.correlate_and_process", side_effect=ValueError("Simulated DB Failure")):
        await worker.process_message(mock_msg)

    # Verify requeue_with_backoff called with retry_count + 1 = 2 and backoff = 2000 * 2^1 = 4000ms
    mock_manager.requeue_with_backoff.assert_called_once_with(
        envelope_retry, retry_count=2, backoff_ms=4000
    )
    mock_manager.publish_to_dlq.assert_not_called()

    # 2. Test DLQ Routing Path (retry_count >= QUEUE_MAX_RETRIES)
    mock_manager.requeue_with_backoff.reset_mock()
    envelope_dlq = dict(envelope_retry, retry_count=settings.QUEUE_MAX_RETRIES)
    mock_msg_dlq = MagicMock()
    mock_msg_dlq.process = MagicMock()
    mock_msg_dlq.process.return_value.__aenter__ = AsyncMock()
    mock_msg_dlq.process.return_value.__aexit__ = AsyncMock()
    mock_msg_dlq.body = str(envelope_dlq).replace("'", '"').encode("utf-8")

    with patch("app.queues.worker.IngestService.correlate_and_process", side_effect=ValueError("Simulated Fatal Error")):
        await worker.process_message(mock_msg_dlq)

    # Verify publish_to_dlq called
    mock_manager.requeue_with_backoff.assert_not_called()
    assert mock_manager.publish_to_dlq.called
    print("✅ Worker Retry and DLQ Routing test passed!")
