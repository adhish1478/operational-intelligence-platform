from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background worker
    from app.integrations.gmail_worker import start_gmail_polling_worker
    polling_task = asyncio.create_task(start_gmail_polling_worker())
    
    yield
    
    # Shutdown: Graceful cancellation
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
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
