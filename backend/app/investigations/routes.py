import uuid
from typing import Any
from fastapi import status, APIRouter, Depends, HTTPException
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