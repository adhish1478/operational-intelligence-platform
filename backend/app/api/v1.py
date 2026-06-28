from fastapi import APIRouter
from app.auth.routes import router as auth_router
from app.organizations.routes import router as org_router

api_router = APIRouter()

# Mount authentication routes
api_router.include_router(auth_router)
api_router.include_router(org_router)

# TODO: Add future routes here (e.g. organizations, investigations, integrations)
