import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
from sqlalchemy import select
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import decode_token, encrypt_credentials
from app.api.deps import DBSessionDep
from app.integrations.models import Integration

router = APIRouter(prefix="/slack", tags=["integrations"])


class SlackConfigPayload(BaseModel):
    channel_id: str
    channel_name: str


@router.get("/authorize")
async def slack_authorize(token: str):
    """
    Initiates the Slack OAuth v2 flow.
    Verifies the user session token and redirects to Slack's authorization server.
    """
    try:
        # Decode the JWT token to verify user session context
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Construct the Slack redirect authorization URL
    # Bot scopes needed: channels:read (list channels) and chat:write (post reports)
    slack_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={settings.SLACK_CLIENT_ID}"
        f"&scope=channels:read,chat:write"
        f"&redirect_uri={settings.SLACK_REDIRECT_URI}"
        f"&state={token}"
    )
    return RedirectResponse(url=slack_url)


@router.get("/callback")
async def slack_callback(db: DBSessionDep, code: str, state: str):
    """
    Slack OAuth callback receiver. Exchanges code for bot access token,
    creates/updates the Integration, and closes the popup.
    """
    # 1. Decode state (JWT token) to retrieve user context
    try:
        payload = decode_token(state)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid state token")
    except Exception:
        raise HTTPException(status_code=401, detail="Auth state expired or invalid")

    # 2. Fetch user to locate their active organization workspace
    from app.auth.models import User
    from sqlalchemy.orm import selectinload

    statement = select(User).where(User.id == uuid.UUID(user_id)).options(selectinload(User.memberships))
    res = await db.execute(statement)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User record not found")

    if not user.memberships:
        raise HTTPException(status_code=400, detail="User has no registered organization workspace")

    organization_id = user.memberships[0].organization_id

    # 3. Exchange code for Slack Access Token
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            "https://slack.com/api/oauth.v2.access",
            headers={"User-Agent": "Sigint-AI-Platform"},
            data={
                "client_id": settings.SLACK_CLIENT_ID,
                "client_secret": settings.SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.SLACK_REDIRECT_URI
            }
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Slack OAuth code exchange failed")

    token_data = token_resp.json()
    if not token_data.get("ok"):
        error_desc = token_data.get("error", "No access token returned")
        raise HTTPException(status_code=400, detail=f"Slack OAuth error: {error_desc}")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access token in Slack response")

    # Encrypt credentials securely before committing
    encrypted_creds = encrypt_credentials({"access_token": access_token})

    # 4. Save/update integration record in PostgreSQL
    statement = select(Integration).where(
        Integration.organization_id == organization_id,
        Integration.platform == "slack"
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
            platform="slack",
            credentials_encrypted=encrypted_creds,
            config={},
            status="active"
        )
    db.add(integration)
    await db.commit()

    # Return HTML response containing script to notify parent window and close popup
    html_content = """
    <html>
    <head>
      <script>
        if (window.opener) {
          window.opener.postMessage({ type: "OIP_INTEGRATION_CONNECTED", platform: "slack" }, "*");
        }
        window.close();
      </script>
    </head>
    <body>
      <p style="font-family: monospace; font-size: 12px; text-align: center; margin-top: 50px;">
        Slack connected successfully. Closing window...
      </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.get("/{integration_id}/channels")
async def get_slack_channels(
    integration_id: uuid.UUID,
    db: DBSessionDep
):
    """
    Fetches all public channels from Slack that the bot has access to.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if not integration or integration.platform != "slack":
        raise HTTPException(status_code=404, detail="Slack integration not found")

    # 2. Decrypt access token
    from app.core.security import decrypt_credentials
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        access_token = creds.get("access_token")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt integration credentials")

    if not access_token:
        raise HTTPException(status_code=400, detail="Integration missing access token")

    # 3. Query Slack conversations.list API
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://slack.com/api/conversations.list?types=public_channel,private_channel&exclude_archived=true&limit=100",
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Sigint-AI-Platform"
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch channels from Slack API")

    slack_data = response.json()
    if not slack_data.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack API error: {slack_data.get('error')}")

    channels = slack_data.get("channels", [])

    return [
        {
            "id": channel.get("id"),
            "name": channel.get("name"),
            "is_private": channel.get("is_private")
        }
        for channel in channels
    ]


@router.post("/{integration_id}/config")
async def update_slack_config(
    integration_id: uuid.UUID,
    payload: SlackConfigPayload,
    db: DBSessionDep
):
    """
    Saves the selected Slack channel target to the integration's JSONB config column.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if not integration or integration.platform != "slack":
        raise HTTPException(status_code=404, detail="Slack integration not found")

    # 2. Update config JSONB column directly
    new_config = dict(integration.config or {})
    new_config["channel_id"] = payload.channel_id
    new_config["channel_name"] = payload.channel_name

    # 3. Save and commit changes
    integration.config = new_config
    db.add(integration)
    await db.commit()

    return {"status": "success", "config": new_config}
