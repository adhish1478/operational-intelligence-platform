import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.integrations.models import Integration
from app.core.security import encrypt_credentials, decrypt_credentials, hash_password
from app.integrations.gmail_worker import sync_gmail_integration, refresh_google_token
from app.db.mongo import get_mongo_db

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def clean_mongo():
    """Ensure the MongoDB evidence collection is empty before and after each test."""
    db = get_mongo_db()
    await db.evidence.delete_many({})
    yield
    await db.evidence.delete_many({})


async def test_refresh_google_token(db_session: AsyncSession):
    # Setup Tenant Org
    org = Organization(name="Gmail Refresh Org", slug="gmail-refresh-org")
    db_session.add(org)
    await db_session.flush()

    # Setup Integration
    integration = Integration(
        organization_id=org.id,
        platform="gmail",
        credentials_encrypted=encrypt_credentials({
            "access_token": "old_token",
            "refresh_token": "my_refresh_token"
        }),
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # Mock Google OAuth token refresh response
    mock_response = httpx.Response(
        status_code=200,
        json={"access_token": "new_access_token", "refresh_token": "new_refresh_token"}
    )

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        creds = {"access_token": "old_token", "refresh_token": "my_refresh_token"}
        new_token = await refresh_google_token(integration, creds, db_session)
        
        assert new_token == "new_access_token"
        mock_post.assert_called_once()
        
        # Verify db updated
        await db_session.refresh(integration)
        updated_creds = decrypt_credentials(integration.credentials_encrypted)
        assert updated_creds["access_token"] == "new_access_token"
        assert updated_creds["refresh_token"] == "new_refresh_token"


async def test_sync_gmail_integration(db_session: AsyncSession):
    # Setup Tenant
    user = User(email="gmail-test@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Gmail Test Org", slug="gmail-test-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    integration = Integration(
        organization_id=org.id,
        platform="gmail",
        credentials_encrypted=encrypt_credentials({
            "access_token": "valid_token",
            "refresh_token": "some_refresh"
        }),
        config={"query": "subject:alert", "last_checked_time": 1000000},
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # Mock message list response
    list_response = httpx.Response(
        status_code=200,
        json={"messages": [{"id": "msg_123"}]}
    )
    
    # Mock message details response
    details_response = httpx.Response(
        status_code=200,
        json={
            "id": "msg_123",
            "snippet": "The production server has crashed!",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Sentry Alert: Server crashed"},
                    {"name": "From", "value": "alerts@sentry.io"}
                ]
            }
        }
    )

    async def mock_get(url, *args, **kwargs):
        if "messages/msg_123" in url:
            return details_response
        return list_response

    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        await sync_gmail_integration(integration, db_session)
        
        # Verify that an investigation was auto-created in PostgreSQL
        from app.investigations.models import Investigation
        statement = select(Investigation).where(Investigation.organization_id == org.id)
        res = await db_session.execute(statement)
        invs = res.scalars().all()
        assert len(invs) == 1
        assert "Sentry Alert" in invs[0].title
        
        # Verify evidence was added to MongoDB
        mongo_db = get_mongo_db()
        evidences = await mongo_db.evidence.find({"investigation_id": str(invs[0].id)}).to_list(length=10)
        assert len(evidences) == 1
        assert evidences[0]["summary"] == "Sentry Alert: Server crashed"
        assert evidences[0]["author_name"] == "alerts@sentry.io"
