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


async def test_jira_connect_success(client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]):
    # Mock Jira api/3/myself return value
    mock_resp = httpx.Response(status_code=200, json={"active": True, "displayName": "Atlassian Developer"})

    with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
        response = await client.post(
            "/api/v1/integrations/jira/connect",
            json={
                "host_url": "my-domain.atlassian.net",
                "email": "dev@company.com",
                "api_token": "token-123"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify call parameters
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert "https://my-domain.atlassian.net/rest/api/3/myself" in call_url

        # Check PostgreSQL
        org_id = uuid.UUID(auth_headers["X-Organization-ID"])
        statement = select(Integration).where(
            Integration.organization_id == org_id,
            Integration.platform == "jira"
        )
        res = await db_session.execute(statement)
        integration = res.scalar_one_or_none()
        assert integration is not None
        assert integration.status == "active"

        # Verify encrypted credentials
        creds = decrypt_credentials(integration.credentials_encrypted)
        assert creds["host_url"] == "https://my-domain.atlassian.net"
        assert creds["email"] == "dev@company.com"
        assert creds["api_token"] == "token-123"


async def test_jira_connect_failed(client: AsyncClient, auth_headers: dict[str, str]):
    # Mock Jira unauthorized response
    mock_resp = httpx.Response(status_code=401, text="Unauthorized access token")

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        response = await client.post(
            "/api/v1/integrations/jira/connect",
            json={
                "host_url": "my-domain.atlassian.net",
                "email": "dev@company.com",
                "api_token": "wrong-token"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "jira verification failed" in response.json()["detail"].lower()


async def test_update_jira_config(client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]):
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
        json={"tracked_projects": ["prod", "sec", ""]},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["config"]["tracked_projects"] == ["PROD", "SEC"]

    # Verify db state
    await db_session.refresh(integration)
    assert integration.config["tracked_projects"] == ["PROD", "SEC"]
