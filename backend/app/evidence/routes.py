import uuid
from typing import Any
from sqlalchemy import select
from fastapi import APIRouter, status, Depends, HTTPException
from app.api.deps import DBSessionDep, MongoSessionDep, ActiveOrganizationDep
from app.investigations.services import InvestigationService
from app.evidence.schemas import EvidenceCreate, EvidenceRead
from app.evidence.services import EvidenceService

router = APIRouter(prefix="/investigations", tags=["evidence"])


@router.get("/evidence/recent", response_model=list[EvidenceRead])
async def get_recent_organization_evidence(
    db: DBSessionDep,
    mongo_db: MongoSessionDep,
    org: ActiveOrganizationDep
) -> Any:
    """
    Retrieve the most recent evidence logs across all active investigations for the organization.
    """
    from datetime import timezone
    from app.investigations.models import Investigation
    
    # 1. Fetch active investigations for the organization
    statement = select(Investigation).where(
        Investigation.organization_id == org.id,
        Investigation.status.in_(["open", "investigating"])
    )
    result = await db.execute(statement)
    active_invs = result.scalars().all()
    if not active_invs:
        return []

    inv_ids = [str(inv.id) for inv in active_invs]

    # 2. Query MongoDB for latest evidence matching these investigations
    cursor = mongo_db.evidence.find({"investigation_id": {"$in": inv_ids}}).sort("created_at", -1).limit(10)
    documents = await cursor.to_list(length=10)

    evidence_list = []
    for doc in documents:
        doc_id = doc.pop("_id")
        evidence_list.append(
            EvidenceRead(
                id=uuid.UUID(doc_id),
                investigation_id=uuid.UUID(doc["investigation_id"]),
                created_at=doc["created_at"].replace(tzinfo=timezone.utc),
                **{k: v for k, v in doc.items() if k not in ("id", "investigation_id", "created_at")}
            )
        )
    return evidence_list


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
