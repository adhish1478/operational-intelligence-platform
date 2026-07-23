import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.base import Base

# Auto-create the test database if it does not exist yet
def ensure_test_database_exists():
    from sqlalchemy import create_engine, text
    sync_url = settings.sync_database_url
    parts = sync_url.rsplit("/", 1)
    admin_url = f"{parts[0]}/postgres"
    test_db_name = f"{settings.POSTGRES_DB}_test"
    
    try:
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": test_db_name}
            )
            exists = result.scalar() is not None
            if not exists:
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
        engine.dispose()
    except Exception as e:
        print(f"Warning: Could not verify/create test database: {e}")

ensure_test_database_exists()

# Point engine to the isolated test database
db_url = settings.async_database_url
parts = db_url.rsplit("/", 1)
test_db_url = f"{parts[0]}/{settings.POSTGRES_DB}_test"

engine = create_async_engine(
    test_db_url,
    pool_pre_ping=True
)

TestSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# Set environment to testing mode to isolate test databases
settings.ENVIRONMENT = "testing"

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_db():
    """Ensure database tables exist before running any tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


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
