from fastapi import APIRouter, status
from app.api.deps import DBSessionDep, ActiveOrganizationDep
from app.reports.schemas import ReportDigest
from app.reports.services import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/digest", response_model=ReportDigest, status_code=status.HTTP_200_OK)
async def get_weekly_reports_digest(
    db: DBSessionDep,
    org: ActiveOrganizationDep
) -> ReportDigest:
    """
    Retrieve aggregated weekly metrics and SLA statuses for the active tenant organization.
    """
    return await ReportService.generate_weekly_digest(db, org.id)
