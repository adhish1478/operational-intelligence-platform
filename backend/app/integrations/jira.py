import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy import select
from pydantic import BaseModel

from app.core.security import encrypt_credentials, decode_token
from app.api.deps import DBSessionDep, TokenDep
from app.integrations.models import Integration

router = APIRouter(prefix="/jira", tags=["integrations"])


class JiraConnectPayload(BaseModel):
    host_url: str
    email: str
    api_token: str


class JiraConfigPayload(BaseModel):
    tracked_projects: list[str]


@router.post("/connect")
async def jira_connect(
    payload: JiraConnectPayload,
    token: TokenDep,
    db: DBSessionDep
):
    """
    Connects to Atlassian Jira using Host URL, Email, and API Token.
    Validates credentials by querying Atlassian's myself endpoint.
    """
    # 1. Clean/Validate Host URL format
    host_url = payload.host_url.strip().rstrip("/")
    if not host_url.startswith(("http://", "https://")):
        host_url = f"https://{host_url}"

    # 2. Decode user session token to locate organization
    try:
        token_data = decode_token(token)
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session token")

    from app.auth.models import User
    from sqlalchemy.orm import selectinload

    statement = select(User).where(User.id == uuid.UUID(user_id)).options(selectinload(User.memberships))
    res = await db.execute(statement)
    user = res.scalar_one_or_none()

    if not user or not user.memberships:
        raise HTTPException(status_code=404, detail="User organization workspace not found")

    organization_id = user.memberships[0].organization_id

    # 3. Ping Jira API with Basic Auth credentials to validate
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(
                f"{host_url}/rest/api/3/myself",
                headers={"User-Agent": "Sigint-AI-Platform"},
                auth=(payload.email, payload.api_token)
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to connect to Jira host '{host_url}': {str(e)}"
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Jira verification failed (status {response.status_code}): {response.text}"
        )

    # 4. Save/update integration record
    creds = {
        "host_url": host_url,
        "email": payload.email,
        "api_token": payload.api_token
    }
    encrypted_creds = encrypt_credentials(creds)

    statement = select(Integration).where(
        Integration.organization_id == organization_id,
        Integration.platform == "jira"
    )
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if integration:
        integration.credentials_encrypted = encrypted_creds
        integration.status = "active"
        integration.last_synced_at = datetime.utcnow()
    else:
        integration = Integration(
            organization_id=organization_id,
            platform="jira",
            credentials_encrypted=encrypted_creds,
            config={},
            status="active"
        )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    return {"status": "success", "integration_id": integration.id}


@router.post("/{integration_id}/config")
async def update_jira_config(
    integration_id: uuid.UUID,
    payload: JiraConfigPayload,
    db: DBSessionDep
):
    """
    Saves the list of tracked Project Keys to the integration's JSONB config column.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if not integration or integration.platform != "jira":
        raise HTTPException(status_code=404, detail="Jira integration not found")

    # Clean project keys to uppercase/stripped
    cleaned_projects = [key.strip().upper() for key in payload.tracked_projects if key.strip()]

    # 2. Update config JSONB column directly
    new_config = dict(integration.config or {})
    new_config["tracked_projects"] = cleaned_projects

    # 3. Save and commit changes
    integration.config = new_config
    db.add(integration)
    await db.commit()

    return {"status": "success", "config": new_config}
