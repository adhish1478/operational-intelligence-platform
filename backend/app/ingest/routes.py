import uuid
import logging
from typing import Any
from fastapi import APIRouter, status, Depends, HTTPException
from app.api.deps import DBSessionDep, MongoSessionDep
from app.integrations.services import IntegrationService
from app.ingest.services import IngestService
from app.queues.rabbitmq import rabbitmq_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


async def dispatch_ingest_event(db, mongo_db, integration, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatches incoming webhook payload to RabbitMQ event queue.
    Falls back to synchronous in-process correlation if RabbitMQ is offline.
    """
    platform = integration.platform
    org_id = str(integration.organization_id)

    try:
        event_id = await rabbitmq_manager.publish_event(
            platform=platform,
            payload=payload,
            organization_id=org_id
        )
        return {
            "status": "queued",
            "event_id": event_id,
            "platform": platform,
            "organization_id": org_id,
            "mode": "async_queue"
        }
    except Exception as queue_err:
        logger.warning(f"RabbitMQ queue publish failed ({queue_err}). Falling back to synchronous processing.")
        return await IngestService.correlate_and_process(db, mongo_db, integration, payload)


@router.post("/slack", status_code=status.HTTP_200_OK)
async def receive_global_slack_webhook(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    payload: dict[str, Any]
) -> Any:
    """
    Static multi-tenant Slack Event Subscription webhook receiver.
    Resolves tenant workspace dynamically using payload['team_id'].
    """
    # 1. Slack URL Verification Challenge handler
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    team_id = payload.get("team_id") or payload.get("event", {}).get("team")

    # 2. Locate active Slack integration in DB by team_id
    from sqlalchemy import select
    from app.integrations.models import Integration

    statement = select(Integration).where(
        Integration.platform == "slack",
        Integration.status == "active"
    )
    res = await db.execute(statement)
    active_slack_integrations = res.scalars().all()

    integration = None
    if team_id:
        for i in active_slack_integrations:
            cfg = i.config or {}
            if cfg.get("team_id") == team_id:
                integration = i
                break

    # Fallback to first active Slack integration if team_id not matched
    if not integration and active_slack_integrations:
        integration = active_slack_integrations[0]

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active Slack integration found for workspace team_id '{team_id}'"
        )

    # 3. Dispatch to RabbitMQ queue or process fallback
    return await dispatch_ingest_event(db, mongo_db, integration, payload)


@router.post("/jira", status_code=status.HTTP_200_OK)
async def receive_global_jira_webhook(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    payload: dict[str, Any]
) -> Any:
    """
    Static multi-tenant Jira Webhook receiver.
    Resolves active Jira integration dynamically.
    """
    from sqlalchemy import select
    from app.integrations.models import Integration

    statement = select(Integration).where(
        Integration.platform == "jira",
        Integration.status == "active"
    )
    res = await db.execute(statement)
    active_jira_integrations = res.scalars().all()

    if not active_jira_integrations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Jira integration found"
        )

    integration = active_jira_integrations[0]
    return await dispatch_ingest_event(db, mongo_db, integration, payload)


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
        
    # 3. Dispatch event to RabbitMQ queue
    return await dispatch_ingest_event(db, mongo_db, integration, payload)
