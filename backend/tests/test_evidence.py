import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.organizations.models import Organization, Membership
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


async def test_evidence_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Tenant User, Org, and Investigation
    user = User(email="triage@org.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Aero Corp", slug="aero")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Create investigation
    inv = Investigation(
        organization_id=org.id,
        title="Database Outage",
        severity="critical",
        status="open"
    )
    db_session.add(inv)
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "triage@org.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 2. Add Evidence (POST)
    evidence_payload = {
        "type": "slack",
        "summary": "Reported database connection pool exhaust by customer support",
        "author_name": "Support Bot",
        "source_url": "https://slack.com/archives/C12345/p16723223",
        "metadata": {
            "channel_id": "C12345",
            "message_text": "Is the database down? Getting 500s on checkout page.",
            "severity_score": 0.95
        }
    }
    
    response = await client.post(
        f"/api/v1/investigations/{inv.id}/evidence",
        json=evidence_payload,
        headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "slack"
    assert data["summary"] == "Reported database connection pool exhaust by customer support"
    assert data["metadata"]["channel_id"] == "C12345"
    assert "id" in data
    assert "created_at" in data

    # 3. Retrieve Chronological Evidence Feed (GET)
    # Add a second piece of evidence
    second_payload = {
        "type": "github",
        "summary": "Commit #a8b32c: Adjusted pool_size settings",
        "author_name": "Dev Alice",
        "source_url": "https://github.com/org/repo/commit/a8b32c",
        "metadata": {
            "commit_sha": "a8b32c",
            "changed_files": ["db/session.py"]
        }
    }
    response_2 = await client.post(
        f"/api/v1/investigations/{inv.id}/evidence",
        json=second_payload,
        headers=headers
    )
    assert response_2.status_code == 201
    
    # Fetch list
    response = await client.get(f"/api/v1/investigations/{inv.id}/evidence", headers=headers)
    assert response.status_code == 200
    feed = response.json()
    assert len(feed) == 2
    
    # Check chronological order (first created should be first)
    assert feed[0]["type"] == "slack"
    assert feed[1]["type"] == "github"
    assert feed[0]["metadata"]["channel_id"] == "C12345"
    assert feed[1]["metadata"]["commit_sha"] == "a8b32c"


async def test_evidence_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # Setup two separate users, orgs, and investigations
    u1 = User(email="tenant1@org.com", password_hash=hash_password("password"))
    u2 = User(email="tenant2@org.com", password_hash=hash_password("password"))
    db_session.add_all([u1, u2])
    await db_session.commit()

    org1 = Organization(name="Tenant 1", slug="t1")
    org2 = Organization(name="Tenant 2", slug="t2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    db_session.add(Membership(user_id=u1.id, organization_id=org1.id, role="owner"))
    db_session.add(Membership(user_id=u2.id, organization_id=org2.id, role="owner"))
    await db_session.commit()

    inv_t1 = Investigation(
        organization_id=org1.id,
        title="Org 1 Leak",
        severity="low",
        status="open"
    )
    db_session.add(inv_t1)
    await db_session.commit()

    # Login as User 2 (Org 2)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "tenant2@org.com", "password": "password"})
    token2 = login_resp.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}", "X-Organization-ID": str(org2.id)}

    # 1. User 2 tries to POST evidence to Org 1's investigation -> 403 Forbidden
    payload = {
        "type": "alert",
        "summary": "Malicious alert injection attempt",
        "metadata": {"hack": "yes"}
    }
    response = await client.post(
        f"/api/v1/investigations/{inv_t1.id}/evidence",
        json=payload,
        headers=headers2
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

    # 2. User 2 tries to GET evidence from Org 1's investigation -> 403 Forbidden
    response = await client.get(
        f"/api/v1/investigations/{inv_t1.id}/evidence",
        headers=headers2
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]

    # 3. Request with invalid non-existent UUID investigation -> 404 Not Found
    random_uuid = uuid.uuid4()
    response = await client.get(
        f"/api/v1/investigations/{random_uuid}/evidence",
        headers=headers2
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
