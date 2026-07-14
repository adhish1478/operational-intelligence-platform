from fastapi import APIRouter
from app.auth.routes import router as auth_router
from app.organizations.routes import router as org_router
from app.investigations.routes import router as inv_router
from app.evidence.routes import router as evidence_router
from app.integrations.routes import router as integrations_router
from app.ingest.routes import router as ingest_router

api_router = APIRouter()

# Mount authentication routes
api_router.include_router(auth_router)
api_router.include_router(org_router)
api_router.include_router(inv_router)
api_router.include_router(evidence_router)
api_router.include_router(integrations_router)
api_router.include_router(ingest_router)



