import pytest
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.investigations.models import Investigation
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

async def test_generate_weekly_reports_digest(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Tenant user, org, and membership
    user = User(email="manager@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Operations Org", slug="ops-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "manager@tenant.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    now = datetime.now(timezone.utc)

    # 2. Seed various investigations to test stats
    # Inv 1: Created 5 hours ago, critical severity (SLA limit 4 hours -> Breach), Title contains "database"
    inv1 = Investigation(
        organization_id=org.id,
        title="Production Postgres Database connection timed out",
        severity="critical",
        status="open",
        detected_at=now - timedelta(hours=5)
    )
    # Inv 2: Created 10 hours ago, high severity (SLA limit 12 hours, 10h is > 9.6h -> Warning), Title contains "api"
    inv2 = Investigation(
        organization_id=org.id,
        title="Gateway checkout API slow response",
        severity="high",
        status="investigating",
        detected_at=now - timedelta(hours=10)
    )
    # Inv 3: Created 2 hours ago, medium severity (SLA limit 24 hours -> Normal), Title contains "kubernetes" (Infrastructure)
    inv3 = Investigation(
        organization_id=org.id,
        title="Kubernetes master memory leak detected",
        severity="medium",
        status="open",
        detected_at=now - timedelta(hours=2)
    )
    # Inv 4: Created 1 day ago, resolved status -> Resolved
    inv4 = Investigation(
        organization_id=org.id,
        title="Test slack event log",
        severity="low",
        status="resolved",
        detected_at=now - timedelta(days=1)
    )
    # Inv 5: Created 10 days ago, low severity (SLA limit 48 hours -> Breach), active status -> Created out of 7 days window
    inv5 = Investigation(
        organization_id=org.id,
        title="Minor UI formatting issues on settings page",
        severity="low",
        status="open",
        detected_at=now - timedelta(days=10)
    )
    db_session.add_all([inv1, inv2, inv3, inv4, inv5])
    await db_session.commit()

    # 3. Query Reports Endpoint
    response = await client.get("/api/v1/reports/digest", headers=headers)
    assert response.status_code == 200
    digest = response.json()

    # 4. Assert correctness of aggregated metrics
    assert digest["organization_id"] == str(org.id)
    # Total created in last 7 days = Inv 1, 2, 3, 4 (4 incidents)
    assert digest["total_created_last_7_days"] == 4
    # Total resolved in last 7 days = Inv 4 (1 incident)
    assert digest["total_resolved_last_7_days"] == 1
    # Total active = Inv 1, 2, 3, 5 (4 incidents)
    assert digest["total_active"] == 4
    
    # SLA checks
    # Warnings = Inv 2 (1 incident)
    assert digest["sla_warnings"] == 1
    # Breaches = Inv 1 (5h > 4h), Inv 5 (10d > 48h) (2 incidents)
    assert digest["sla_breaches"] == 2

    # Severity distribution
    assert digest["severity_distribution"]["critical"] == 1
    assert digest["severity_distribution"]["high"] == 1
    assert digest["severity_distribution"]["medium"] == 1
    assert digest["severity_distribution"]["low"] == 1  # Inv 5 is active low

    # Category distribution
    assert digest["category_distribution"]["database"] == 1       # Inv 1
    assert digest["category_distribution"]["api"] == 1            # Inv 2
    assert digest["category_distribution"]["infrastructure"] == 1 # Inv 3
    assert digest["category_distribution"]["other"] == 1          # Inv 5


async def test_weekly_reports_digest_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # Setup two users in Org 1 and Org 2
    u1 = User(email="user1@tenant.com", password_hash=hash_password("password"))
    u2 = User(email="user2@tenant.com", password_hash=hash_password("password"))
    db_session.add_all([u1, u2])
    await db_session.commit()

    org1 = Organization(name="Tenant 1", slug="tenant1")
    org2 = Organization(name="Tenant 2", slug="tenant2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    db_session.add(Membership(user_id=u1.id, organization_id=org1.id, role="owner"))
    db_session.add(Membership(user_id=u2.id, organization_id=org2.id, role="owner"))
    await db_session.commit()

    # Login as User 2 (Org 2)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "user2@tenant.com", "password": "password"})
    token2 = login_resp.json()["access_token"]
    
    # User 2 queries digest with Org 1's ID in header -> 403 Forbidden
    headers = {"Authorization": f"Bearer {token2}", "X-Organization-ID": str(org1.id)}
    response = await client.get("/api/v1/reports/digest", headers=headers)
    assert response.status_code == 403
