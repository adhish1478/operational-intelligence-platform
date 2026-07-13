import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.integrations.models import Integration
from app.integrations.services import IntegrationService
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio

async def test_integration_credentials_encryption(db_session: AsyncSession):
    # Verify that encryption helper works and db helper successfully decrypts
    org = Organization(name="Test Encryption Org", slug="encrypt-org")
    db_session.add(org)
    await db_session.flush()

    raw_credentials = {"bot_token": "xoxb-123456789-secret", "verification_token": "abcde12345"}
    
    from app.integrations.schemas import IntegrationCreate
    integration_in = IntegrationCreate(
        platform="slack",
        credentials=raw_credentials
    )
    
    db_obj = await IntegrationService.create_integration(db_session, org.id, integration_in)
    
    # 1. Assert credentials are encrypted and stored as a cipher string, not plaintext
    assert db_obj.credentials_encrypted != str(raw_credentials)
    assert "xoxb-" not in db_obj.credentials_encrypted
    
    # 2. Assert decryption utility successfully restores original credentials
    decrypted = IntegrationService.get_decrypted_credentials(db_obj)
    assert decrypted["bot_token"] == "xoxb-123456789-secret"
    assert decrypted["verification_token"] == "abcde12345"


async def test_integrations_api_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup user, org, membership
    user = User(email="admin@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Admin Tenant", slug="admin-tenant")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={"email": "admin@tenant.com", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 2. Connect Integration (POST) - Slack
    slack_payload = {
        "platform": "slack",
        "credentials": {
            "bot_token": "xoxb-valid-slack-bot-token"
        }
    }
    response = await client.post("/api/v1/integrations/", json=slack_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "slack"
    assert data["status"] == "active"
    assert "id" in data
    # Ensure credentials do NOT leak in response
    assert "credentials" not in data
    assert "bot_token" not in data
    
    integration_id = data["id"]

    # Connect another integration - Gmail (Pivoted feature)
    gmail_payload = {
        "platform": "gmail",
        "credentials": {
            "client_secret": "gmail_oauth_client_secret_xyz"
        }
    }
    response_gmail = await client.post("/api/v1/integrations/", json=gmail_payload, headers=headers)
    assert response_gmail.status_code == 201
    assert response_gmail.json()["platform"] == "gmail"

    # 3. List Integrations (GET)
    response = await client.get("/api/v1/integrations/", headers=headers)
    assert response.status_code == 200
    list_data = response.json()
    assert len(list_data) == 2
    # Check credentials are masked/omitted from list response
    assert "credentials" not in list_data[0]
    assert "credentials" not in list_data[1]

    # 4. Test Connection (POST /{id}/test)
    # Testing valid slack token
    response = await client.post(f"/api/v1/integrations/{integration_id}/test", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "verified" in response.json()["message"].lower()

    # Testing invalid Gmail token (missing keys)
    gmail_id = response_gmail.json()["id"]
    await client.patch(
        f"/api/v1/integrations/{gmail_id}", 
        json={"credentials": {"client_id": "test_id"}}, # client_secret is missing now
        headers=headers
    )
    response = await client.post(f"/api/v1/integrations/{gmail_id}/test", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "invalid gmail credentials" in response.json()["message"].lower()

    # 5. Delete Integration (DELETE)
    response = await client.delete(f"/api/v1/integrations/{integration_id}", headers=headers)
    assert response.status_code == 204

    # Verify deleted
    response = await client.get("/api/v1/integrations/", headers=headers)
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == gmail_id


async def test_integrations_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # Setup two separate users, orgs
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

    # Create integration for Org 1
    integration_org1 = Integration(
        organization_id=org1.id,
        platform="jira",
        credentials_encrypted="some-encrypted-string",
        status="active"
    )
    db_session.add(integration_org1)
    await db_session.commit()

    # Login as User 2 (Org 2)
    login_resp = await client.post("/api/v1/auth/login", json={"email": "user2@tenant.com", "password": "password"})
    token2 = login_resp.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}", "X-Organization-ID": str(org2.id)}

    # User 2 tries to access Org 1's integration -> 403 Forbidden
    # Test connection
    response = await client.post(f"/api/v1/integrations/{integration_org1.id}/test", headers=headers2)
    assert response.status_code == 403
    
    # Update settings
    response = await client.patch(f"/api/v1/integrations/{integration_org1.id}", json={"status": "disconnected"}, headers=headers2)
    assert response.status_code == 403

    # Delete integration
    response = await client.delete(f"/api/v1/integrations/{integration_org1.id}", headers=headers2)
    assert response.status_code == 403
