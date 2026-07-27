import uuid
import asyncio
from typing import Any
from sqlalchemy import select
from fastapi import status, APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.api.deps import DBSessionDep, ActiveOrganizationDep, MongoSessionDep, CurrentUserDep
from app.investigations.schemas import (
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationRead,
    DiagnosisRead
)
from app.investigations.services import InvestigationService, DiagnosisService

router= APIRouter(prefix='/investigations', tags=['investigations'])

@router.post('/', response_model=InvestigationRead, status_code= status.HTTP_201_CREATED)
async def create_new_investigation(
    db:DBSessionDep,
    org: ActiveOrganizationDep,
    investigation_in: InvestigationCreate
) -> Any:
    # Injecting ActiveOrganizationDep ensures:
    # 1. Header X-Organization-ID exists.
    # 2. Requester belongs to this organization.
    return await InvestigationService.create_investigation(db, org.id, investigation_in)

@router.get('/', response_model=list[InvestigationRead])
async def list_investigations(
    db: DBSessionDep,
    org: ActiveOrganizationDep
) -> Any:
    # Lists investigations strictly for the active tenant Organization
    return await InvestigationService.list_organization_investigations(db, org.id)

@router.get('/{id}', response_model = InvestigationRead)
async def get_investigation(
    db:DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> Any:
    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code= 404, detail= "investigation not found")
    
    # strict tenant isolation check
    if investigation.organization_id != org.id:
        raise HTTPException(status_code= 403, detail= 'Forbidden: Result belongs to another tenant')

    return investigation

@router.patch('/{id}', response_model= InvestigationRead)
async def update_investigation_details(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID,
    investigation_update: InvestigationUpdate
) -> Any:
    investigation = await InvestigationService.get_investigation_by_id(db, id)

    if not investigation:
        raise HTTPException(status_code= 404, detail="investigation not found")
    
    if investigation.organization_id != org.id:
        raise HTTPException(status_code= 403, detail="Forbidden: result belongs to another tenant")

    return await InvestigationService.update_investigation(db, investigation, investigation_update)


@router.post('/{id}/diagnose', response_model=DiagnosisRead, status_code=status.HTTP_201_CREATED)
async def run_investigation_diagnosis(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    org: ActiveOrganizationDep,
    current_user: CurrentUserDep,
    id: uuid.UUID
) -> Any:
    """
    Trigger an AI-led diagnosis summarizing the compiled evidence timeline for the investigation.
    """
    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
        
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Result belongs to another tenant")
        
    return await DiagnosisService.generate_diagnosis_report(
        db, mongo_db, investigation, current_user.id
    )


@router.get('/{id}/diagnose/stream')
async def stream_investigation_diagnosis(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    org: ActiveOrganizationDep,
    current_user: CurrentUserDep,
    id: uuid.UUID
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint streaming real-time DAG multi-agent execution milestones to the frontend.
    """
    import json
    from fastapi.responses import StreamingResponse

    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
        
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Result belongs to another tenant")

    async def event_generator():
        queue = asyncio.Queue()

        async def callback(event_name: str, data: dict[str, Any]):
            await queue.put({"event": event_name, "data": data})

        async def run_analysis():
            try:
                diag = await DiagnosisService.generate_diagnosis_report(
                    db, mongo_db, investigation, current_user.id, event_callback=callback
                )
                await queue.put({
                    "event": "finished",
                    "data": {
                        "diagnosis_id": str(diag.id),
                        "report_summary": diag.report_summary,
                        "technical_rca": diag.technical_rca,
                        "business_impact": diag.business_impact,
                        "remediation_plan": diag.remediation_plan,
                    }
                })
            except Exception as e:
                await queue.put({"event": "error", "data": {"message": str(e)}})
            finally:
                await queue.put(None) # Sentinel to close stream

        asyncio.create_task(run_analysis())

        while True:
            item = await queue.get()
            if item is None:
                break
            event_type = item["event"]
            payload = json.dumps(item["data"])
            yield f"event: {event_type}\ndata: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get('/{id}/diagnoses', response_model=list[DiagnosisRead])
async def list_investigation_diagnoses(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> Any:
    """
    Fetch all diagnosis reports (including structured multi-agent outputs) for an investigation.
    """
    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
        
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Result belongs to another tenant")

    return await DiagnosisService.list_investigation_diagnoses(db, id)


@router.post('/{id}/share-slack')
async def share_investigation_to_slack(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> Any:
    """
    Share the latest AI Diagnosis report directly to the configured Slack triage channel.
    """
    # 1. Fetch investigation and check tenant
    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Result belongs to another tenant")

    # 2. Fetch the latest diagnosis report summary
    from sqlalchemy import desc
    from app.investigations.models import Diagnosis
    diag_statement = select(Diagnosis).where(Diagnosis.investigation_id == id).order_by(desc(Diagnosis.created_at))
    diag_res = await db.execute(diag_statement)
    latest_diagnosis = diag_res.scalars().first()
    if not latest_diagnosis:
        raise HTTPException(status_code=400, detail="Please run AI Diagnosis first before sharing.")

    # 3. Retrieve Slack active integration
    from app.integrations.models import Integration
    from app.core.security import decrypt_credentials
    int_statement = select(Integration).where(
        Integration.organization_id == org.id,
        Integration.platform == "slack",
        Integration.status == "active"
    )
    int_res = await db.execute(int_statement)
    integration = int_res.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=400, detail="Slack integration not connected or active.")

    # 4. Decrypt bot token and read channel configuration
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        slack_token = creds.get("access_token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt Slack credentials: {str(e)}")

    if not slack_token:
        raise HTTPException(status_code=400, detail="Missing Slack bot credentials.")

    channel_id = integration.config.get("channel_id")
    channel_name = integration.config.get("channel_name", "#alerts")
    if not channel_id:
        raise HTTPException(status_code=400, detail="No Slack triage channel configured.")

    # 5. POST to Slack chat.postMessage
    import httpx
    text_content = (
        f"🚨 *Incident Escalation Alert: {investigation.title}*\n"
        f"Severity: `{investigation.severity.upper()}` | Status: `{investigation.status.upper()}`\n\n"
        f"*AI Diagnosis & Root Cause Summary:*\n"
        f"{latest_diagnosis.report_summary}\n"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {slack_token}"},
                json={"channel": channel_id, "text": text_content}
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Slack request failed: {str(e)}")

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Slack returned HTTP error: {response.text}")

    slack_res = response.json()
    if not slack_res.get("ok"):
        raise HTTPException(status_code=400, detail=f"Slack API error: {slack_res.get('error')}")

    return {"status": "success", "channel": channel_name}


@router.post('/{id}/escalate-jira')
async def escalate_investigation_to_jira(
    db: DBSessionDep,
    org: ActiveOrganizationDep,
    id: uuid.UUID
) -> Any:
    """
    Create a task issue on Jira Cloud representing this investigation,
    attaching the latest AI Diagnosis report as the ticket description.
    """
    # 1. Fetch investigation and check tenant
    investigation = await InvestigationService.get_investigation_by_id(db, id)
    if not investigation:
        raise HTTPException(status_code=404, detail="investigation not found")
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Result belongs to another tenant")

    # 2. Fetch the latest diagnosis report summary
    from sqlalchemy import desc
    from app.investigations.models import Diagnosis
    diag_statement = select(Diagnosis).where(Diagnosis.investigation_id == id).order_by(desc(Diagnosis.created_at))
    diag_res = await db.execute(diag_statement)
    latest_diagnosis = diag_res.scalars().first()
    if not latest_diagnosis:
        raise HTTPException(status_code=400, detail="Please run AI Diagnosis first before escalating.")

    # 3. Retrieve Jira active integration
    from app.integrations.models import Integration
    from app.core.security import decrypt_credentials
    int_statement = select(Integration).where(
        Integration.organization_id == org.id,
        Integration.platform == "jira",
        Integration.status == "active"
    )
    int_res = await db.execute(int_statement)
    integration = int_res.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=400, detail="Jira integration not connected or active.")

    # 4. Decrypt credentials and load config project
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        access_token = creds.get("access_token")
        cloud_id = creds.get("cloud_id")
        site_url = creds.get("site_url")
        
        # Legacy fallback
        host_url = creds.get("host_url") or site_url
        email = creds.get("email")
        api_token = creds.get("api_token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decrypt Jira credentials: {str(e)}")

    is_oauth = bool(access_token and cloud_id)
    is_basic = bool(host_url and email and api_token)

    if not is_oauth and not is_basic:
        raise HTTPException(status_code=400, detail="Missing Jira connection credentials. Please reconnect Jira integration.")

    project_list = integration.config.get("tracked_projects", [])
    project_key = None
    if project_list:
        p0 = project_list[0]
        project_key = p0.get("key") if isinstance(p0, dict) else str(p0)

    # 5. POST to Jira issue creation endpoint
    # 5. POST to Jira issue creation endpoint
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Dynamically resolve target project key from Jira API if not specified
        if not project_key and is_oauth:
            try:
                pj_resp = await client.get(
                    f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/project/search",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
                )
                if pj_resp.status_code == 200:
                    values = pj_resp.json().get("values", [])
                    if values:
                        project_key = values[0].get("key")
            except Exception:
                pass

        if not project_key:
            project_key = "KAN"

        jira_payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": f"[OIP Alert] {investigation.title}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Operational incident escalated from OIP.\n\n"
                                        f"AI Diagnosis Report:\n{latest_diagnosis.report_summary}"
                                    )
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"
                }
            }
        }

        try:
            if is_oauth:
                req_url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/issue"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                response = await client.post(req_url, headers=headers, json=jira_payload)
                
                # Automatic 401 token refresh & retry
                if response.status_code == 401 and creds.get("refresh_token"):
                    from app.core.config import settings
                    from app.core.security import encrypt_credentials
                    
                    rf_resp = await client.post(
                        "https://auth.atlassian.com/oauth/token",
                        json={
                            "grant_type": "refresh_token",
                            "client_id": settings.JIRA_CLIENT_ID,
                            "client_secret": settings.JIRA_CLIENT_SECRET,
                            "refresh_token": creds["refresh_token"],
                        }
                    )
                    if rf_resp.status_code == 200:
                        rf_data = rf_resp.json()
                        new_access_token = rf_data.get("access_token")
                        new_refresh_token = rf_data.get("refresh_token") or creds["refresh_token"]
                        creds["access_token"] = new_access_token
                        creds["refresh_token"] = new_refresh_token
                        integration.credentials_encrypted = encrypt_credentials(creds)
                        db.add(integration)
                        await db.commit()

                        headers["Authorization"] = f"Bearer {new_access_token}"
                        response = await client.post(req_url, headers=headers, json=jira_payload)
            else:
                req_url = f"{host_url}/rest/api/3/issue"
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                response = await client.post(req_url, headers=headers, auth=(email, api_token), json=jira_payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Jira request failed: {str(e)}")

    if response.status_code != 201:
        raise HTTPException(
            status_code=400,
            detail=f"Jira issue creation failed (status {response.status_code}): {response.text}"
        )

    res_data = response.json()
    key = res_data.get("key", "UNKNOWN-KEY")
    base_site_url = site_url or host_url or "https://atlassian.net"
    ticket_url = f"{base_site_url}/browse/{key}"

    # 6. Append Jira ticket key reference back to the investigation suggestion_action for persistence
    esc_suffix = f"\n\n[Escalated to Jira ticket: {key}]"
    if not investigation.suggestion_action:
        investigation.suggestion_action = esc_suffix.strip()
    elif esc_suffix not in investigation.suggestion_action:
        investigation.suggestion_action += esc_suffix

    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    return {"status": "success", "key": key, "url": ticket_url}