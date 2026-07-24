from fastapi.openapi.utils import status_code_ranges
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
from sqlalchemy import select
from pydantic import BaseModel

import logging
from app.core.config import settings
from app.core.security import decode_token, encrypt_credentials
from app.api.deps import DBSessionDep
from app.auth.services import AuthService
from app.integrations.models import Integration

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["integrations"])

@router.get("/authorize")
async def github_authorize(token: str):
    """
    Initiates the GitHub OAuth flow.
    Verifies the user session token and redirects their browser to GitHub.
    """
    try:
        # Decode the JWT token to verify user session context
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Construct the GitHub redirect authorization URL
    # We pass the JWT token inside 'state' to securely decode it in the callback
    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=repo,admin:repo_hook,read:org"
        f"&state={token}"
    )
    return RedirectResponse(url=github_url)


@router.get("/callback")
async def github_callback(db: DBSessionDep, code: str, state: str):
    """
    OAuth callback receiver. Exchages code for access token,
    creates/updates the Integration, and redirects back to the frontend.
    """
    # 1. Decode state (JWT token) to retrieve user context
    try:
        payload = decode_token(state)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid state token")
    except Exception:
        raise HTTPException(status_code=401, detail="Auth state expired or invalid")

    # 2. Fetch user to locate their active organization workspace (eager loading memberships)
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

    # 3. Exchange code for GitHub Access Token (with 30s timeout and User-Agent headers)
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
                "User-Agent": "Sigint-AI-Platform"
            },
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI
            }
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="OAuth code exchange failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        error_desc = token_data.get("error_description", "No access token returned")
        raise HTTPException(status_code=400, detail=f"GitHub OAuth error: {error_desc}")

    # Encrypt credentials securely before committing
    encrypted_creds = encrypt_credentials({"access_token": access_token})

    # 4. Save/update integration record in PostgreSQL
    statement = select(Integration).where(
        Integration.organization_id == organization_id,
        Integration.platform == "github"
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
            platform="github",
            credentials_encrypted=encrypted_creds,
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
          window.opener.postMessage({ type: "OIP_INTEGRATION_CONNECTED", platform: "github" }, "*");
        }
        window.close();
      </script>
    </head>
    <body>
      <p style="font-family: monospace; font-size: 12px; text-align: center; margin-top: 50px;">
        GitHub connected successfully. Closing window...
      </p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)



class TrackReposRequest(BaseModel):
    repos: list[str]

@router.get("/{integration_id}/repos")
async def get_github_repos(
    integration_id: uuid.UUID,
    db: DBSessionDep
    ):
    """
    Fetches all repositories from GitHub that the active connection token has access to.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res= await db.execute(statement)
    integration = res.scalar_one_or_none()

    if not integration or integration.platform != "github":
        raise HTTPException(status_code=404, detail="integration config not found")

    # 2. decript creds to extract access token
    from app.core.security import decrypt_credentials
    try:
        creds= decrypt_credentials(integration.credentials_encrypted)
        access_token = creds.get("access_token")
    except Exception:
        raise HTTPException(status_code=500, detail="failed to decrypt credentials")
    if not access_token:
        raise HTTPException(status_code=400, detail="Integration is not connected or missing")
    
    # 3. Query GitHub API for user repositories
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Sigint-AI-Platform"
            }
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch repositories from GitHub: {response.text}"
        )
    
    repos = response.json()

    # Return formatted list of repository details safely
    return [
        {
            "id": repo.get("id"),
            "full_name": repo.get("full_name"),
            "private": repo.get("private"),
            "default_branch": repo.get("default_branch"),
            "description": repo.get("description"),
            "language": repo.get("language"),
            "pushed_at": repo.get("pushed_at")
        }
        for repo in repos
    ]

@router.post("/{integration_id}/track")
async def update_tracked_repositories(
    integration_id: uuid.UUID,
    payload: TrackReposRequest,
    db: DBSessionDep
):
    """
    Saves the list of selected repository slugs to the integration's configuration.
    """
    # 1. Fetch integration
    statement = select(Integration).where(Integration.id == integration_id)
    res = await db.execute(statement)
    integration = res.scalar_one_or_none()
    
    if not integration or integration.platform != "github":
        raise HTTPException(status_code=404, detail="Integration configuration not found")
        
    # 2. Update the config JSONB column directly
    new_config = dict(integration.config or {})
    new_config["tracked_repos"] = payload.repos

    # 3. Decrypt credentials to get access_token for automatic GitHub API webhook registration
    from app.core.security import decrypt_credentials
    access_token = None
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        access_token = creds.get("access_token")
    except Exception:
        pass

    # Construct public target webhook URL
    base_url = settings.WEBHOOK_BASE_URL or "http://localhost:8000"
    webhook_target_url = f"{base_url.rstrip('/')}{settings.API_V1_STR}/ingest/{integration.id}"

    # 4. Automatically register GitHub Webhooks via GitHub REST API if access_token is present
    registered_webhooks = []
    if access_token:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for repo_slug in payload.repos:
                try:
                    hook_resp = await client.post(
                        f"https://api.github.com/repos/{repo_slug}/hooks",
                        headers={
                            "Authorization": f"token {access_token}",
                            "Accept": "application/vnd.github+json",
                            "User-Agent": "Sigint-AI-Platform"
                        },
                        json={
                            "name": "web",
                            "active": True,
                            "events": ["pull_request", "workflow_run", "issues", "push"],
                            "config": {
                                "url": webhook_target_url,
                                "content_type": "json",
                                "insecure_ssl": "0"
                            }
                        }
                    )
                    logger.info(f"GitHub Webhook API registration for {repo_slug} [{webhook_target_url}]: Status {hook_resp.status_code} - {hook_resp.text}")
                    if hook_resp.status_code in [201, 422]:  # 201 Created or 422 Already Exists
                        registered_webhooks.append(repo_slug)
                except Exception as hook_err:
                    logger.error(f"Failed to register GitHub webhook for {repo_slug}: {hook_err}")

    # 5. Save and commit changes
    integration.config = new_config
    db.add(integration)
    await db.commit()

    return {
        "status": "success",
        "config": new_config,
        "webhook_target_url": webhook_target_url,
        "registered_webhooks": registered_webhooks
    }