# backend/tests/test_investigations.py
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.investigations.models import Investigation
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

async def test_investigation_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup Tenant User and Org
    user = User(email="triage@org.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Aero Corp", slug="aero")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "triage@org.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 2. Create Investigation (POST)
    payload = {
        "title": "API Gateway Memory Leak",
        "description": "High memory consumption on prod-gateway container.",
        "severity": "critical",
        "status": "open"
    }
    response = await client.post("/api/v1/investigations/", json=payload, headers=headers)
    assert response.status_code == 201
    inv_id = response.json()["id"]
    assert response.json()["title"] == "API Gateway Memory Leak"
    assert response.json()["status"] == "open"

    # 3. List Investigations (GET)
    response = await client.get("/api/v1/investigations/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == inv_id

    # 4. Fetch Details (GET /{id})
    response = await client.get(f"/api/v1/investigations/{inv_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["description"] == "High memory consumption on prod-gateway container."

    # 5. Update Status (PATCH /{id})
    response = await client.patch(
        f"/api/v1/investigations/{inv_id}",
        json={"status": "investigating", "suggestion_action": "Revert release #882"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "investigating"
    assert response.json()["suggestion_action"] == "Revert release #882"


async def test_investigation_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # Setup two completely separate organizations and members
    u1 = User(email="user1@tenant.com", password_hash=hash_password("password"))
    u2 = User(email="user2@tenant.com", password_hash=hash_password("password"))
    db_session.add_all([u1, u2])
    await db_session.commit()

    org1 = Organization(name="Org 1", slug="org1")
    org2 = Organization(name="Org 2", slug="org2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    db_session.add(Membership(user_id=u1.id, organization_id=org1.id, role="owner"))
    db_session.add(Membership(user_id=u2.id, organization_id=org2.id, role="owner"))
    await db_session.commit()

    # Create an investigation inside Org 1
    inv_org1 = Investigation(
        organization_id=org1.id,
        title="Incident Tenant 1",
        severity="medium",
        status="open"
    )
    db_session.add(inv_org1)
    await db_session.commit()

    # Login as User 2 (member of Org 2)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "user2@tenant.com", "password": "password"})
    token2 = login_resp.json()["access_token"]
    
    # User 2 tries to fetch Org 1's investigation using Org 2's tenant ID header -> 403 Forbidden
    headers2 = {"Authorization": f"Bearer {token2}", "X-Organization-ID": str(org2.id)}
    response = await client.get(f"/api/v1/investigations/{inv_org1.id}", headers=headers2)
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]