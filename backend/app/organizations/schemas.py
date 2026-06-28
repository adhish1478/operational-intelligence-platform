import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Display name of the organization")
    slug: str = Field(..., min_length=2, max_length=100, description="URL-friendly slug")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class MembershipBase(BaseModel):
    role: str = Field("member", description="RBAC role: owner, admin, member, viewer")


class MembershipCreate(MembershipBase):
    user_id: uuid.UUID


class MembershipUpdate(BaseModel):
    role: str = Field(..., description="New role for the membership")


class MembershipRead(MembershipBase):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
