import uuid
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field

class IntegrationBase(BaseModel):
    platform: Literal["slack", "github", "jira", "gmail"] = Field(..., description="Target service platform")
    status: Literal["active", "error", "disconnected"] = Field("active")

class IntegrationCreate(IntegrationBase):
    credentials: dict[str, Any] = Field(..., description="Connection credentials payload (e.g. API keys, secrets)")

class IntegrationUpdate(BaseModel):
    credentials: dict[str, Any] | None = Field(None, description="Optional connection credentials to update")
    config: dict[str, Any] | None = Field(None, description="Optional configuration dict to update")
    status: Literal["active", "error", "disconnected"] | None = Field(None)

class IntegrationRead(IntegrationBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    last_synced_at: datetime | None
    created_at: datetime
    config: dict[str, Any] = {}

    model_config = {
        "from_attributes": True
    }
