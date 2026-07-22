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

router = APIRouter(prefix="/gmail", tags=["integrations"])


class GmailConfigPayload(BaseModel):
    query: str


@router.get("/authorize")
async def gmail_authorize(token: str):
    """
    Initiates the Google OAuth 2.0 flow for Gmail.
    Verifies user session token and redirects to Google's consent page.
    """
    try:
        # Decode the JWT token to verify user session context
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Construct Google redirect authorization URL
    # Scope requested: gmail.readonly (read emails)
    # access_type=offline & prompt=consent are requested to guarantee we get a refresh_token
    google_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.readonly"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={token}"
    )
    return RedirectResponse(url=google_url)


@router.get("/callback")
async def gmail_callback(db: DBSessionDep, code: str, state: str):
    """
    Google OAuth callback receiver. Exchanges code for access and refresh tokens,
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

    # 3. Exchange code for Google Access & Refresh Tokens
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            headers={"User-Agent": "Sigint-AI-Platform"},
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Google OAuth code exchange failed: {token_resp.text}")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access token in Google response")

    # Encrypt credentials securely before committing.
    # Note: refresh_token is optional if user already authorized before, but offline access type tries to fetch it.
    creds = {"access_token": access_token}
    if refresh_token:
        creds["refresh_token"] = refresh_token

    encrypted_creds = encrypt_credentials(creds)

    # 4. Save/update integration record in PostgreSQL
    statement = select(Integration).where(
        Integration.organization_id == organization_id,
        Integration.platform == "gmail"
    )
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if integration:
        # If we didn't receive a new refresh token (Google only sends it on first consent),
        # preserve the existing refresh token!
        if not refresh_token:
            from app.core.security import decrypt_credentials
            try:
                old_creds = decrypt_credentials(integration.credentials_encrypted)
                if old_creds.get("refresh_token"):
                    creds["refresh_token"] = old_creds["refresh_token"]
                    encrypted_creds = encrypt_credentials(creds)
            except Exception:
                pass

        integration.credentials_encrypted = encrypted_creds
        integration.status = "active"
        integration.last_synced_at = datetime.utcnow()
    else:
        integration = Integration(
            organization_id=organization_id,
            platform="gmail",
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
          window.opener.postMessage({ type: "OIP_INTEGRATION_CONNECTED", platform: "gmail" }, "*");
        }
        window.close();
      </script>
    </head>
    <body>
      <p style="font-family: monospace; font-size: 12px; text-align: center; margin-top: 50px;">
        Gmail connected successfully. Closing window...
      </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.post("/{integration_id}/config")
async def update_gmail_config(
    integration_id: uuid.UUID,
    payload: GmailConfigPayload,
    db: DBSessionDep
):
    """
    Saves the Google Search Query filter to the integration's JSONB config column.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()

    if not integration or integration.platform != "gmail":
        raise HTTPException(status_code=404, detail="Gmail integration not found")

    # 2. Update config JSONB column directly
    new_config = dict(integration.config or {})
    new_config["query"] = payload.query

    # 3. Save and commit changes
    integration.config = new_config
    db.add(integration)
    await db.commit()

    return {"status": "success", "config": new_config}
