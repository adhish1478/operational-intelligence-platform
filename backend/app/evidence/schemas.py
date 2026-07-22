import uuid
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field

class EvidenceBase(BaseModel):
    type: Literal["slack", "github", "jira", "gmail", "alert"] = Field(..., description="Type of evidence source")
    summary: str = Field(..., min_length=3, max_length=255, description="Brief summary description of the evidence")
    author_name: str | None = Field(None, max_length=100)
    source_url: str | None = Field(None, max_length=1024)
    metadata: dict[str, Any] | None = Field(None, description="Unstructured integration details payload")

class EvidenceCreate(EvidenceBase):
    pass

class EvidenceRead(EvidenceBase):
    id: uuid.UUID
    investigation_id: uuid.UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
