import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

# Suppress noisy PyMongo topology & heartbeat logging
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.command").setLevel(logging.WARNING)
logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)

# Cache clients by the running event loop to prevent "Event loop is closed" errors in pytest
_mongo_clients = {}

def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Returns the motor database instance, caching the client per running event loop
    to ensure compatibility with pytest's per-test event loops.
    Automatically uses MONGODB_TEST_DB when ENVIRONMENT is set to 'testing'.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    db_name = settings.MONGODB_TEST_DB if settings.ENVIRONMENT == "testing" else settings.MONGODB_DB

    import os
    mongo_url = settings.MONGODB_URL
    if "localhost" in mongo_url and os.environ.get("POSTGRES_SERVER") == "db":
        mongo_url = "mongodb://mongodb:27017"

    if loop is not None:
        if loop not in _mongo_clients:
            _mongo_clients[loop] = AsyncIOMotorClient(mongo_url)
        client = _mongo_clients[loop]
    else:
        client = AsyncIOMotorClient(mongo_url)
        
    return client[db_name]
