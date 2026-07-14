import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.integrations.models import Integration
from app.investigations.models import Investigation
from app.db.mongo import get_mongo_db
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(autouse=True)
async def clean_mongo():
    """Ensure the MongoDB evidence collection is empty before and after each test."""
    db = get_mongo_db()
    await db.evidence.delete_many({})
    yield
    await db.evidence.delete_many({})


async def test_webhook_ingest_correlation(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Tenant User, Org, and Integration
    user = User(email="analyst@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Correlate Org", slug="correlate-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Create Slack Integration
    integration = Integration(
        organization_id=org.id,
        platform="slack",
        credentials_encrypted="some-encrypted-secrets",
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # Pre-create an active investigation matching a keyword (e.g. "outage")
    active_inv = Investigation(
        organization_id=org.id,
        title="Database Outage on Prod-West",
        severity="critical",
        status="open"
    )
    db_session.add(active_inv)
    await db_session.commit()

    # 2. Ingest Slack Webhook payload matching the "Outage" or "Database" keyword
    slack_payload = {
        "event": {
            "text": "Sentry: database connection limits hit. Possible outage.",
            "user": "USLACKBOT123",
            "ts": "16723223.001"
        }
    }
    
    response = await client.post(
        f"/api/v1/ingest/{integration.id}",
        json=slack_payload
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "correlated"
    assert result["investigation_id"] == str(active_inv.id)
    
    # 3. Check MongoDB: verify evidence is linked to the existing investigation
    mongo_db = get_mongo_db()
    evidence_doc = await mongo_db.evidence.find_one({"_id": result["evidence_id"]})
    assert evidence_doc is not None
    assert evidence_doc["investigation_id"] == str(active_inv.id)
    assert evidence_doc["type"] == "slack"
    assert "Sentry: database connection limits hit" in evidence_doc["summary"]


async def test_webhook_ingest_autocreation(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Tenant User, Org, and Integration (Jira)
    user = User(email="jira@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Auto Create Org", slug="autocreate-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    integration = Integration(
        organization_id=org.id,
        platform="jira",
        credentials_encrypted="some-encrypted-secrets",
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # 2. Ingest Jira payload. No active investigations exist in database -> Should auto-create one
    jira_payload = {
        "issue": {
            "key": "OPS-847",
            "fields": {
                "summary": "Kubernetes API server memory leak",
                "creator": {
                    "displayName": "Jira Robot"
                }
            }
        }
    }
    
    response = await client.post(
        f"/api/v1/ingest/{integration.id}",
        json=jira_payload
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "created"
    new_inv_id = result["investigation_id"]
    
    # 3. Verify PostgreSQL: Check that new investigation is created
    statement = select(Investigation).where(Investigation.id == uuid.UUID(new_inv_id))
    inv_result = await db_session.execute(statement)
    new_inv = inv_result.scalar_one_or_none()
    assert new_inv is not None
    assert new_inv.title == "Jira Issue OPS-847: Kubernetes API server memory leak"
    assert new_inv.status == "open"
    assert new_inv.severity == "high" # auto-mapped from memory leak/failed/error keywords

    # 4. Verify MongoDB: Check that evidence is correctly saved
    mongo_db = get_mongo_db()
    evidence_doc = await mongo_db.evidence.find_one({"_id": result["evidence_id"]})
    assert evidence_doc is not None
    assert evidence_doc["investigation_id"] == new_inv_id
    assert evidence_doc["type"] == "jira"


async def test_webhook_ingest_disconnected(client: AsyncClient, db_session: AsyncSession):
    # Setup Tenant User, Org, and disconnected Integration
    user = User(email="test@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Disconnect Org", slug="disconnect-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    integration = Integration(
        organization_id=org.id,
        platform="github",
        credentials_encrypted="some-secrets",
        status="disconnected"
    )
    db_session.add(integration)
    await db_session.commit()

    # POST payload to disconnected integration -> 400 Bad Request
    response = await client.post(
        f"/api/v1/ingest/{integration.id}",
        json={"test": "data"}
    )
    assert response.status_code == 400
    assert "disconnected" in response.json()["detail"].lower()


async def test_webhook_ingest_not_found(client: AsyncClient):
    # POST to non-existent integration ID -> 404 Not Found
    random_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/ingest/{random_id}",
        json={"test": "data"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
