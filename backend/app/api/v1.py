from fastapi import APIRouter
from app.auth.routes import router as auth_router
from app.organizations.routes import router as org_router
from app.investigations.routes import router as inv_router
from app.evidence.routes import router as evidence_router
from app.integrations.routes import router as integrations_router
from app.integrations.github import router as github_oauth_router
from app.integrations.slack import router as slack_oauth_router
from app.integrations.gmail import router as gmail_oauth_router
from app.integrations.jira import router as jira_oauth_router
from app.ingest.routes import router as ingest_router
from app.reports.routes import router as reports_router

api_router = APIRouter()

# Mount authentication routes
api_router.include_router(auth_router)
api_router.include_router(org_router)
api_router.include_router(inv_router)
api_router.include_router(evidence_router)
api_router.include_router(integrations_router)
api_router.include_router(github_oauth_router, prefix="/integrations")
api_router.include_router(slack_oauth_router, prefix="/integrations")
api_router.include_router(gmail_oauth_router, prefix="/integrations")
api_router.include_router(jira_oauth_router, prefix="/integrations")
api_router.include_router(ingest_router)
api_router.include_router(reports_router)




