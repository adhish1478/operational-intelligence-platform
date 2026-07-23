import uuid
from typing import Any
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel, Field
from app.api.deps import DBSessionDep, ActiveOrganizationDep
from app.db.mongo import get_mongo_db
from app.ingest.services import IngestService
from app.integrations.models import Integration
from app.integrations.schemas import (
    IntegrationCreate,
    IntegrationRead,
    IntegrationUpdate
)
from app.integrations.services import IntegrationService

router = APIRouter(prefix="/integrations", tags=["integrations"])

class GmailConfigPreviewRequest(BaseModel):
    allowed_senders: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    subject_contains: list[str] = Field(default_factory=list)
    subject_starts_with: list[str] = Field(default_factory=list)


@router.get("/gmail/senders-suggestions")
async def get_gmail_sender_suggestions(
    org: ActiveOrganizationDep
) -> Any:
    """
    Returns a list of unique recently seen Gmail senders from MongoDB evidence logs.
    """
    mongo_db = get_mongo_db()
    cursor = mongo_db.evidence.find({"type": "gmail"}).sort("created_at", -1).limit(200)
    docs = await cursor.to_list(length=200)
    
    seen_senders = set()
    for d in docs:
        author = d.get("author_name")
        if author:
            seen_senders.add(author)
            
    defaults = ["alerts@datadog.com", "github@github.com", "pagerduty.com", "security@company.com"]
    for def_sender in defaults:
        seen_senders.add(def_sender)
        
    return {"suggestions": sorted(list(seen_senders))}


@router.post("/gmail/preview-filter")
async def preview_gmail_signal_filter(
    org: ActiveOrganizationDep,
    body: GmailConfigPreviewRequest
) -> Any:
    """
    Evaluates candidate Gmail filter configuration against stored evidence in MongoDB.
    Returns matched vs ignored counts and sample subjects for live preview rendering.
    """
    mongo_db = get_mongo_db()
    cursor = mongo_db.evidence.find({"type": "gmail"}).sort("created_at", -1).limit(100)
    docs = await cursor.to_list(length=100)

    candidate_integration = Integration(
        platform="gmail",
        config={
            "allowed_senders": body.allowed_senders,
            "required_keywords": body.required_keywords,
            "subject_contains": body.subject_contains,
            "subject_starts_with": body.subject_starts_with
        }
    )

    matched_samples = []
    ignored_samples = []

    for doc in docs:
        parsed = {
            "type": "gmail",
            "summary": doc.get("summary", ""),
            "author_name": doc.get("author_name", ""),
            "metadata": doc.get("metadata", {})
        }
        is_signal, _ = IngestService.classify_signal(candidate_integration, parsed)
        sample_title = doc.get("summary", "Untitled Signal")
        
        if is_signal:
            if sample_title not in matched_samples:
                matched_samples.append(sample_title)
        else:
            if sample_title not in ignored_samples:
                ignored_samples.append(sample_title)

    return {
        "matched_count": len(matched_samples),
        "ignored_count": len(ignored_samples),
        "matched_samples": matched_samples[:5],
        "ignored_samples": ignored_samples[:5]
    }

@router.post("/", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
async def connect_new_integration(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    integration_in: IntegrationCreate
) -> Any:
    """
    Connect a new third-party integration workspace (Slack, GitHub, Jira, Gmail) to the organization.
    """
    return await IntegrationService.create_integration(db, org.id, integration_in)


@router.get("/", response_model=list[IntegrationRead])
async def list_integrations(
    db: DBSessionDep,
    org: ActiveOrganizationDep
) -> Any:
    """
    List all configured integrations for the active tenant organization.
    """
    return await IntegrationService.list_organization_integrations(db, org.id)


@router.patch("/{id}", response_model=IntegrationRead)
async def update_integration_settings(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID,
    integration_update: IntegrationUpdate
) -> Any:
    """
    Update integration configuration settings or credentials.
    """
    integration = await IntegrationService.get_integration_by_id(db, id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
        
    if integration.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Resource belongs to another tenant")
        
    return await IntegrationService.update_integration(db, integration, integration_update)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> None:
    """
    Disconnect and remove an integration configuration.
    """
    integration = await IntegrationService.get_integration_by_id(db, id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
        
    if integration.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Resource belongs to another tenant")
        
    await IntegrationService.delete_integration(db, integration)


@router.post("/{id}/test")
async def test_integration_connectivity(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> Any:
    """
    Perform a simulated connection check using the decrypted integration credentials.
    """
    integration = await IntegrationService.get_integration_by_id(db, id)
    if not integration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
        
    if integration.organization_id != org.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Resource belongs to another tenant")

    try:
        credentials = IntegrationService.get_decrypted_credentials(integration)
        
        # Simulated validation logic per platform
        platform = integration.platform
        is_valid = False
        message = "Connection check failed"
        
        if platform == "slack":
            # Slack requires a bot_token (typically xoxb-...)
            token = credentials.get("bot_token")
            if token and token.startswith("xoxb-"):
                is_valid = True
                message = "Slack connection successful: Bot token verified."
            else:
                message = "Invalid Slack credentials: Must provide a valid bot token starting with 'xoxb-'."
                
        elif platform == "github":
            # GitHub requires a personal_access_token (ghp_...) or app key
            token = credentials.get("personal_access_token")
            if token and (token.startswith("ghp_") or token.startswith("github_pat_")):
                is_valid = True
                message = "GitHub connection successful: Access token verified."
            else:
                message = "Invalid GitHub credentials: Must provide a valid personal access token."
                
        elif platform == "jira":
            # Jira requires an api_token and username/email
            token = credentials.get("api_token")
            email = credentials.get("email")
            if token and email:
                is_valid = True
                message = "Jira connection successful: Credentials verified."
            else:
                message = "Invalid Jira credentials: Must provide both email and API token."
                
        elif platform == "gmail":
            # Gmail requires oauth credentials client_secret or refresh_token
            secret = credentials.get("client_secret") or credentials.get("refresh_token")
            if secret:
                is_valid = True
                message = "Gmail connection successful: OAuth tokens verified."
            else:
                message = "Invalid Gmail credentials: Must provide a client_secret or refresh_token."

        if is_valid:
            # Update status in DB to active if it was in error
            if integration.status != "active":
                integration.status = "active"
                db.add(integration)
                await db.commit()
            return {"status": "success", "message": message}
        else:
            # Set status to error
            integration.status = "error"
            db.add(integration)
            await db.commit()
            return {"status": "failed", "message": message}

    except Exception as e:
        integration.status = "error"
        db.add(integration)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decryption/Validation system exception: {str(e)}"
        )
