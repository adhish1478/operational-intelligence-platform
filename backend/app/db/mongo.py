import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

# Cache clients by the running event loop to prevent "Event loop is closed" errors in pytest
_mongo_clients = {}

def get_mongo_db() -> AsyncIOMotorDatabase:
    """
    Returns the motor database instance, caching the client per running event loop
    to ensure compatibility with pytest's per-test event loops.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop is not None:
        if loop not in _mongo_clients:
            _mongo_clients[loop] = AsyncIOMotorClient(settings.MONGODB_URL)
        client = _mongo_clients[loop]
    else:
        client = AsyncIOMotorClient(settings.MONGODB_URL)
        
    return client[settings.MONGODB_DB]
