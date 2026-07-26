import pytest
import pytest_asyncio
import uuid
from unittest.mock import patch
import httpx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.integrations.models import Integration
from app.core.security import hash_password, decrypt_credentials

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, db_session: AsyncSession) -> dict[str, str]:
    """Sets up a tenant user, organization, and returns auth headers."""
    user = User(email="jira-analyst@tenant.com", password_hash=hash_password("password"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Jira Test Org", slug="jira-test-org")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Log in to get session token
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "jira-analyst@tenant.com", "password": "password"}
    )
    token = resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(org.id)
    }


async def test_jira_authorize_flow(client: AsyncClient, auth_headers: dict[str, str]):
    """Verifies Jira OAuth 2.0 (3LO) authorization URL generation."""
    token = auth_headers["Authorization"].split(" ")[1]
    response = await client.get(
        f"/api/v1/integrations/jira/authorize?token={token}",
        follow_redirects=False
    )
    assert response.status_code == 307
    assert "https://auth.atlassian.com/authorize" in response.headers["location"]


async def test_update_jira_config(client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]):
    """Verifies Jira project tracking configuration updates."""
    org_id = uuid.UUID(auth_headers["X-Organization-ID"])

    # Create active integration row
    integration = Integration(
        organization_id=org_id,
        platform="jira",
        credentials_encrypted="some-encrypted-bytes",
        config={},
        status="active"
    )
    db_session.add(integration)
    await db_session.commit()

    # Post tracked projects configuration
    response = await client.post(
        f"/api/v1/integrations/jira/{integration.id}/config",
        json={"tracked_projects": [{"key": "PROD", "name": "Production"}, {"key": "SEC", "name": "Security"}]},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert len(response.json()["config"]["tracked_projects"]) == 2

    # Verify db state
    await db_session.refresh(integration)
    assert len(integration.config["tracked_projects"]) == 2
