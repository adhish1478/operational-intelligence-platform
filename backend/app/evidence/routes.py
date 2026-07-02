import uuid
from typing import Any
from fastapi import APIRouter, status, Depends, HTTPException
from app.api.deps import DBSessionDep, MongoSessionDep, ActiveOrganizationDep
from app.investigations.services import InvestigationService
from app.evidence.schemas import EvidenceCreate, EvidenceRead
from app.evidence.services import EvidenceService

router = APIRouter(prefix="/investigations", tags=["evidence"])

@router.post("/{investigation_id}/evidence", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def add_evidence_to_investigation(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    org: ActiveOrganizationDep,
    investigation_id: uuid.UUID,
    evidence_in: EvidenceCreate
) -> Any:
    """
    Append a new evidence document to a specific investigation.
    Verifies that the investigation exists and belongs to the active tenant organization.
    """
    # 1. Fetch parent investigation
    investigation = await InvestigationService.get_investigation_by_id(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
        
    # 2. Verify tenant boundary
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Resource belongs to another tenant")
        
    # 3. Create document in MongoDB
    return await EvidenceService.create_evidence(mongo_db, investigation_id, evidence_in)


@router.get("/{investigation_id}/evidence", response_model=list[EvidenceRead])
async def list_investigation_evidence_feed(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    org: ActiveOrganizationDep,
    investigation_id: uuid.UUID
) -> Any:
    """
    Retrieve the chronological evidence feed associated with a specific investigation.
    Verifies that the investigation exists and belongs to the active tenant organization.
    """
    # 1. Fetch parent investigation
    investigation = await InvestigationService.get_investigation_by_id(db, investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
        
    # 2. Verify tenant boundary
    if investigation.organization_id != org.id:
        raise HTTPException(status_code=403, detail="Forbidden: Resource belongs to another tenant")
        
    # 3. Fetch list from MongoDB
    return await EvidenceService.list_investigation_evidence(mongo_db, investigation_id)
