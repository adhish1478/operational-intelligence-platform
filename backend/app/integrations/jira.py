import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
from sqlalchemy import select
from pydantic import BaseModel, Field

import logging
from app.core.config import settings
from app.core.security import decode_token, encrypt_credentials, decrypt_credentials
from app.api.deps import DBSessionDep
from app.auth.services import AuthService
from app.integrations.models import Integration
from app.ingest.services import get_ist_time_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jira", tags=["integrations"])


class JiraConfigPayload(BaseModel):
    project_key: str | None = None
    project_name: str | None = None
    tracked_projects: list[str] = Field(default_factory=list)


async def register_jira_webhook_helper(cloud_id: str, access_token: str) -> None:
    """
    Dynamically register/update the Jira webhook with Atlassian API using WEBHOOK_BASE_URL.
    """
    try:
        webhook_base = settings.WEBHOOK_BASE_URL or "http://localhost:8000"
        webhook_target = f"{webhook_base.rstrip('/')}/api/v1/ingest/jira"
        logger.info(f"Registering Jira webhook target: {webhook_target}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Fetch available project keys in Jira workspace for valid JQL filtering
            proj_resp = await client.get(
                f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            project_keys = []
            if proj_resp.status_code == 200 and isinstance(proj_resp.json(), list):
                project_keys = [
                    p.get("key") for p in proj_resp.json()
                    if isinstance(p, dict) and p.get("key")
                ]

            if project_keys:
                keys_formatted = ", ".join(f'"{k}"' for k in project_keys)
                jql_filter = f"project in ({keys_formatted})"
            else:
                jql_filter = 'project != "00000"'

            wh_resp = await client.post(
                f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/webhook",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": webhook_target,
                    "webhooks": [
                        {
                            "events": [
                                "jira:issue_created",
                                "jira:issue_updated",
                                "jira:issue_deleted",
                                "comment_created",
                                "comment_updated",
                                "comment_deleted",
                                "worklog_created",
                                "attachment_created",
                            ],
                            "jqlFilter": jql_filter,
                        }
                    ],
                },
            )
            logger.info(f"Jira webhook registration response [{wh_resp.status_code}]: {wh_resp.text}")
            print(f"[{get_ist_time_str()}] 🔗 Jira Webhook Registration [{wh_resp.status_code}]: {wh_resp.text}")
    except Exception as e:
        logger.warning(f"Failed to auto-register Jira webhook: {e}")


@router.get("/authorize")
async def jira_authorize(token: str):
    """
    Initiates the Atlassian OAuth 2.0 (3LO) flow.
    Verifies the user session token and redirects to Atlassian authorization server.
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    jira_url = (
        f"https://auth.atlassian.com/authorize"
        f"?audience=api.atlassian.com"
        f"&client_id={settings.JIRA_CLIENT_ID}"
        f"&scope=read:jira-work%20write:jira-work%20read:jira-user%20manage:jira-webhook%20offline_access"
        f"&redirect_uri={settings.JIRA_REDIRECT_URI}"
        f"&state={token}"
        f"&response_type=code"
        f"&prompt=consent"
    )
    return RedirectResponse(url=jira_url)


@router.get("/callback")
async def jira_callback(db: DBSessionDep, code: str, state: str):
    """
    OAuth 2.0 callback receiver. Exchanges authorization code for tokens,
    retrieves accessible Jira site resources, and creates/updates the Integration.
    """
    try:
        payload = decode_token(state)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid state token")
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Fetch user with memberships loaded eagerly
    from app.auth.models import User
    from sqlalchemy.orm import selectinload

    statement = select(User).where(User.id == uuid.UUID(user_id)).options(selectinload(User.memberships))
    res = await db.execute(statement)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    organization_id = user.memberships[0].organization_id

    # Exchange code for access token
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            "https://auth.atlassian.com/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": settings.JIRA_CLIENT_ID,
                "client_secret": settings.JIRA_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.JIRA_REDIRECT_URI,
            },
        )
        if token_response.status_code != 200:
            logger.error(f"Failed to exchange Jira OAuth code: {token_response.text}")
            raise HTTPException(status_code=400, detail="Failed to authenticate with Jira")

        token_data = token_response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        # Fetch accessible resources (Jira Cloud Site ID & Site URL)
        resources_resp = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resources_resp.status_code != 200 or not resources_resp.json():
            raise HTTPException(status_code=400, detail="No accessible Jira sites found")

        resources = resources_resp.json()
        primary_site = resources[0]
        cloud_id = primary_site.get("id")
        site_name = primary_site.get("name", "Jira Site")
        site_url = primary_site.get("url", "")

    encrypted_creds = encrypt_credentials(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "cloud_id": cloud_id,
            "site_url": site_url,
        }
    )

    # Check for existing Jira integration
    stmt = select(Integration).where(
        Integration.organization_id == organization_id,
        Integration.platform == "jira",
    )
    res = await db.execute(stmt)
    existing_integration = res.scalars().first()

    if existing_integration:
        existing_config = existing_integration.config or {}
        existing_config.update({
            "cloud_id": cloud_id,
            "site_name": site_name,
            "site_url": site_url,
        })
        existing_integration.credentials_encrypted = encrypted_creds
        existing_integration.status = "active"
        existing_integration.config = existing_config
        existing_integration.updated_at = datetime.utcnow()
        integration = existing_integration
    else:
        integration = Integration(
            organization_id=organization_id,
            platform="jira",
            status="active",
            credentials_encrypted=encrypted_creds,
            config={
                "cloud_id": cloud_id,
                "site_name": site_name,
                "site_url": site_url,
                "tracked_projects": [],
            },
        )
        db.add(integration)

    await db.commit()
    await db.refresh(integration)

    await register_jira_webhook_helper(cloud_id, access_token)

    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Jira Connection Successful</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #0f172a; color: #f8fafc; }
                .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); text-align: center; max-width: 400px; border: 1px solid #334155; }
                h2 { color: #38bdf8; margin-top: 0; }
                p { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }
                .spinner { margin: 20px auto; width: 40px; height: 40px; border: 4px solid rgba(56, 189, 248, 0.1); border-left-color: #38bdf8; border-radius: 50%; animation: spin 1s linear infinite; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Jira Connected!</h2>
                <p>Your Jira workspace has been linked successfully.</p>
                <div class="spinner"></div>
                <p style="font-size: 0.8rem; color: #64748b;">Redirecting back to dashboard...</p>
            </div>
            <script>
                setTimeout(() => {
                    if (window.opener) {
                        window.opener.postMessage({ type: "JIRA_AUTH_SUCCESS" }, "*");
                        window.close();
                    } else {
                        window.location.href = "http://localhost:5173/integrations";
                    }
                }, 1500);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


async def get_valid_jira_access_token(
    db: DBSessionDep,
    integration: Integration
) -> tuple[str | None, str | None]:
    """
    Returns valid (access_token, cloud_id) for Jira integration.
    If access_token is expired (401), automatically uses refresh_token
    to acquire a fresh access_token via POST https://auth.atlassian.com/oauth/token and updates DB!
    """
    creds = decrypt_credentials(integration.credentials_encrypted)
    access_token = creds.get("access_token")
    refresh_token = creds.get("refresh_token")
    cloud_id = creds.get("cloud_id")

    if not access_token or not cloud_id:
        return None, None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if resp.status_code == 200:
                return access_token, cloud_id

            if resp.status_code == 401 and refresh_token:
                logger.info("Jira access_token expired. Refreshing token with Atlassian...")
                token_resp = await client.post(
                    "https://auth.atlassian.com/oauth/token",
                    json={
                        "grant_type": "refresh_token",
                        "client_id": settings.JIRA_CLIENT_ID,
                        "client_secret": settings.JIRA_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                    }
                )
                if token_resp.status_code == 200:
                    t_data = token_resp.json()
                    new_access_token = t_data.get("access_token")
                    new_refresh_token = t_data.get("refresh_token") or refresh_token

                    creds["access_token"] = new_access_token
                    creds["refresh_token"] = new_refresh_token
                    integration.credentials_encrypted = encrypt_credentials(creds)
                    integration.updated_at = datetime.utcnow()
                    db.add(integration)
                    await db.commit()
                    await db.refresh(integration)
                    logger.info("Successfully refreshed Atlassian access token!")
                    return new_access_token, cloud_id
    except Exception as e:
        logger.error(f"Error checking/refreshing Jira access token: {e}")

    return access_token, cloud_id


@router.get("/{integration_id}/projects")
@router.get("/projects")
async def get_jira_projects(
    db: DBSessionDep,
    integration_id: str | None = None,
    token: str | None = None
):
    """
    Fetches Jira projects from the connected Jira site.
    """
    integration = None
    if integration_id:
        stmt = select(Integration).where(
            Integration.id == integration_id,
            Integration.platform == "jira",
            Integration.status == "active",
        )
        res = await db.execute(stmt)
        integration = res.scalars().first()

    if not integration and token:
        try:
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                user = await AuthService.get_user_by_id(db, uuid.UUID(user_id))
                if user and user.memberships:
                    organization_id = user.memberships[0].organization_id
                    stmt = select(Integration).where(
                        Integration.organization_id == organization_id,
                        Integration.platform == "jira",
                        Integration.status == "active",
                    )
                    res = await db.execute(stmt)
                    integration = res.scalars().first()
        except Exception:
            pass

    if not integration:
        return {"projects": []}

    access_token, cloud_id = await get_valid_jira_access_token(db, integration)

    if not access_token or not cloud_id:
        return {"projects": []}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                projects_raw = resp.json()
                projects = [
                    {"key": p.get("key"), "name": p.get("name"), "id": p.get("id")}
                    for p in projects_raw
                    if isinstance(p, dict)
                ]
                return {"projects": projects}
    except Exception as e:
        logger.error(f"Failed to fetch Jira projects: {e}")

    return {"projects": []}


@router.post("/{integration_id}/config")
@router.post("/config")
async def update_jira_config(
    db: DBSessionDep,
    payload: JiraConfigPayload,
    integration_id: str | None = None,
    token: str | None = None
):
    """
    Updates configuration for Jira integration (tracked projects).
    """
    integration = None
    if integration_id:
        stmt = select(Integration).where(
            Integration.id == integration_id,
            Integration.platform == "jira",
            Integration.status == "active",
        )
        res = await db.execute(stmt)
        integration = res.scalars().first()

    if not integration and token:
        try:
            decoded = decode_token(token)
            user_id = decoded.get("sub")
            if user_id:
                user = await AuthService.get_user_by_id(db, uuid.UUID(user_id))
                if user and user.memberships:
                    organization_id = user.memberships[0].organization_id
                    stmt = select(Integration).where(
                        Integration.organization_id == organization_id,
                        Integration.platform == "jira",
                        Integration.status == "active",
                    )
                    res = await db.execute(stmt)
                    integration = res.scalars().first()
        except Exception:
            pass

    if not integration:
        raise HTTPException(status_code=404, detail="Active Jira integration not found")

    current_config = integration.config or {}
    if payload.tracked_projects is not None:
        current_config["tracked_projects"] = payload.tracked_projects
    if payload.project_key:
        current_config["project_key"] = payload.project_key
    if payload.project_name:
        current_config["project_name"] = payload.project_name

    integration.config = current_config
    integration.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(integration)

    # Re-register Jira webhook with current WEBHOOK_BASE_URL
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        decrypted_access_token = creds.get("access_token")
        cloud_id = (integration.config or {}).get("cloud_id")
        if cloud_id and decrypted_access_token:
            await register_jira_webhook_helper(cloud_id, decrypted_access_token)
    except Exception as e:
        logger.warning(f"Failed to re-register Jira webhook on config save: {e}")

    return {"status": "success", "config": integration.config}
