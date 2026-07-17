from datetime import datetime
import uuid
from pydantic import BaseModel, Field

class SeverityDistribution(BaseModel):
    critical: int = Field(0, description="Count of critical severity incidents")
    high: int = Field(0, description="Count of high severity incidents")
    medium: int = Field(0, description="Count of medium severity incidents")
    low: int = Field(0, description="Count of low severity incidents")

class CategoryDistribution(BaseModel):
    database: int = Field(0, description="Count of database-related incidents")
    api: int = Field(0, description="Count of API-related incidents")
    infrastructure: int = Field(0, description="Count of infrastructure-related incidents")
    other: int = Field(0, description="Count of miscellaneous category incidents")

class ReportDigest(BaseModel):
    organization_id: uuid.UUID
    total_created_last_7_days: int
    total_resolved_last_7_days: int
    total_active: int
    sla_warnings: int
    sla_breaches: int
    severity_distribution: SeverityDistribution
    category_distribution: CategoryDistribution
    generated_at: datetime
