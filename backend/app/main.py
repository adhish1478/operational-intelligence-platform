from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Configuration
# Set up origins allowing secure integrations with the frontend application
# In development, wide wildcards are allowed; in production, strict domains are enforced
origins = [
    "http://localhost:5173", # Standard Vite default frontend port
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["healthcheck"], status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """
    Core service health status checker endpoint.
    Used by load-balancers, Kubernetes probes, and docker compose healthchecks.
    """
    return {"status": "healthy"}
