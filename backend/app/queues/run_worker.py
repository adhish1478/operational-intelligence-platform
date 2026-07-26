import asyncio
import logging
import sys
from app.queues.worker import worker_instance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger("worker")


async def main():
    logger.info("🚀 Starting Operational Intelligence Platform RabbitMQ Event Worker...")
    try:
        await worker_instance.start_consumer()
        # Keep worker event loop running indefinitely until interrupted
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Worker process stopped by user.")
    except Exception as e:
        logger.error(f"Worker encountered unhandled error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
