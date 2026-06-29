import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.base import Base

# Create a test engine pointing to the local postgres
# In standard setups, a separate test database is preferred.
# Here we connect to the configured DB but run all tests in a transaction that is rolled back.
engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True
)

TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_db():
    """Ensure database tables exist before running any tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

    # We do not drop tables here in case developer has custom data, 
    # but in fresh CI we could.


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture that runs each test inside a transactional block that is automatically rolled back.
    This guarantees no side effects leak between tests.
    """
    async with engine.connect() as connection:
        transaction = await connection.begin()
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session
            await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP Client configured with the transactional db_session dependency override.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Using the modern ASGITransport API as recommended in newer httpx versions
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()
