import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.investigations.models import Investigation, Diagnosis
from app.evidence.schemas import EvidenceCreate
from app.evidence.services import EvidenceService
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


async def test_run_investigation_diagnosis_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Org, User, and Membership
    user = User(email="diagnostician@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Diagnosis Org", slug="diag-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "diagnostician@tenant.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 2. Create an Investigation
    inv = Investigation(
        organization_id=org.id,
        title="Web Server Timeout Spikes",
        severity="high",
        status="open"
    )
    db_session.add(inv)
    await db_session.commit()

    # 3. Add evidence to MongoDB to compile for diagnosis
    mongo_db = get_mongo_db()
    ev1 = EvidenceCreate(
        type="slack",
        summary="Sentry alert: timeout on /checkout endpoint",
        author_name="Slack Integration",
        source_url=None,
        metadata={"sentry_id": "8472"}
    )
    await EvidenceService.create_evidence(mongo_db, inv.id, ev1)

    ev2 = EvidenceCreate(
        type="github",
        summary="GitHub Commit: Adjusted timeout configurations",
        author_name="Developer Alice",
        source_url="https://github.com/org/repo/commit/123",
        metadata={"commit_hash": "123abcdef"}
    )
    await EvidenceService.create_evidence(mongo_db, inv.id, ev2)

    # 4. Trigger Diagnosis
    response = await client.post(
        f"/api/v1/investigations/{inv.id}/diagnose",
        headers=headers
    )
    assert response.status_code == 201
    result = response.json()
    assert result["investigation_id"] == str(inv.id)
    assert result["triggered_by_id"] == str(user.id)
    assert "report_summary" in result
    assert len(result["report_summary"]) > 0

    # 5. Verify PostgreSQL updates
    # Investigation status should be updated to "investigating" and suggestion_action saved
    await db_session.refresh(inv)
    assert inv.status == "investigating"
    assert inv.suggestion_action == result["report_summary"]

    # Verify a Diagnosis row was created
    statement = select(Diagnosis).where(Diagnosis.investigation_id == inv.id)
    diag_result = await db_session.execute(statement)
    db_diag = diag_result.scalar_one_or_none()
    assert db_diag is not None
    assert db_diag.report_summary == result["report_summary"]


async def test_run_investigation_diagnosis_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # Setup two users in different Orgs
    u1 = User(email="u1@tenant.com", password_hash=hash_password("password"))
    u2 = User(email="u2@tenant.com", password_hash=hash_password("password"))
    db_session.add_all([u1, u2])
    await db_session.commit()

    org1 = Organization(name="Org 1", slug="org1")
    org2 = Organization(name="Org 2", slug="org2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    db_session.add(Membership(user_id=u1.id, organization_id=org1.id, role="owner"))
    db_session.add(Membership(user_id=u2.id, organization_id=org2.id, role="owner"))
    await db_session.commit()

    # Create investigation for Org 1
    inv = Investigation(
        organization_id=org1.id,
        title="Sensitive Outage",
        severity="critical",
        status="open"
    )
    db_session.add(inv)
    await db_session.commit()

    # Login as User 2 (Org 2)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "u2@tenant.com", "password": "password"})
    token2 = login_resp.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}", "X-Organization-ID": str(org2.id)}

    # User 2 tries to trigger diagnosis on Org 1's incident -> 403 Forbidden
    response = await client.post(
        f"/api/v1/investigations/{inv.id}/diagnose",
        headers=headers2
    )
    assert response.status_code == 403


async def test_run_investigation_diagnosis_not_found(client: AsyncClient, db_session: AsyncSession):
    # Setup User and Org
    user = User(email="analyst@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Outage Org", slug="outage-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "analyst@tenant.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # POST to non-existent investigation ID -> 404 Not Found
    random_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/investigations/{random_id}/diagnose",
        headers=headers
    )
    assert response.status_code == 404
