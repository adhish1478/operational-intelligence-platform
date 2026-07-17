import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class InvestigationBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None)
    severity : Literal['critical','high','medium','low'] = Field('medium')
    status: Literal["open", "investigating", "resolved"] = Field("open")
    assigned_to_id: uuid.UUID | None = Field(None)
    suggestion_action : str | None = Field(None)

class InvestigationCreate(InvestigationBase):
    pass

class InvestigationUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = Field(None)
    severity: Literal['critical','high','medium','low'] | None= Field(None)
    status: Literal['open','investigating','resolved'] | None= Field(None)
    assigned_to_id: uuid.UUID | None = Field(None)
    suggestion_action : str | None = Field(None)
    
class InvestigationRead(InvestigationBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    detected_at: datetime

    model_config = {
        'from_attributes': True
    }


class DiagnosisRead(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    triggered_by_id: uuid.UUID | None
    report_summary: str
    created_at: datetime

    model_config = {
        'from_attributes': True
    }

