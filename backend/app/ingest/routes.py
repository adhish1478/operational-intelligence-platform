import uuid
from typing import Any
from fastapi import APIRouter, status, Depends, HTTPException
from app.api.deps import DBSessionDep, MongoSessionDep
from app.integrations.services import IntegrationService
from app.ingest.services import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/{integration_id}", status_code=status.HTTP_200_OK)
async def receive_webhook_payload(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    integration_id: uuid.UUID,
    payload: dict[str, Any]
) -> Any:
    """
    Public webhook receiver endpoint. Processes and correlates raw events to investigations.
    """
    # Slack URL Verification Challenge handler
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # 1. Fetch integration by ID
    integration = await IntegrationService.get_integration_by_id(db, integration_id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook integration configuration not found"
        )
        
    # 2. Check if integration is active
    if integration.status == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload rejected: Integration is currently disconnected"
        )
        
    # 3. Call IngestService to parse, correlate, and save
    result = await IngestService.correlate_and_process(db, mongo_db, integration, payload)
    
    return result
