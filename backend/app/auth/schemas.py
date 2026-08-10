import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------------------------------------------
# User Schemas
# -----------------------------------------------------------------------------

class UserBase(BaseModel):
    email: EmailStr = Field(description="Unique email address of the user")
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128, description="Plaintext password")


class UserUpdate(BaseModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)


class UserRead(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True  # Pydantic v2 ORM compatibility configuration
    }


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# -----------------------------------------------------------------------------
# Token Schemas
# -----------------------------------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Note: Refresh token is delivered via secure HttpOnly cookie, 
    # but we represent it here as an optional response property for alternative clients
    refresh_token: str | None = None


class TokenPayload(BaseModel):
    sub: str | None = None # User ID (subject)
    exp: int | None = None # Expiration timestamp
    type: str | None = None # Token type (access vs refresh)
    
    # TODO: Future RBAC/Multi-Tenant Claims Hook
    # role: str | None = None
    # org_id: str | None = None
