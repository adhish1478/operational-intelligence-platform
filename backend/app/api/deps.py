from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.db.mongo import get_mongo_db
from app.auth.models import User
from app.auth.services import AuthService
from app.organizations.models import Organization

# OAuth2 security scheme for header parsing
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Common Type Aliases for injection clarity
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
MongoSessionDep = Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]



async def get_current_user(db: DBSessionDep, token: TokenDep) -> User:
    """
    FastAPI dependency that extracts, decodes, and validates the incoming JWT access token.
    Returns the User database object if signature is valid, token is unexpired,
    and user exists/is active.
    """
    from app.auth.blocklist import is_token_blocklisted
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if is_token_blocklisted(token):
        raise credentials_exception

    
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception
            
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise credentials_exception

    user = await AuthService.get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user profile"
        )
        
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_active_organization(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    x_organization_id: Annotated[str | None, Header(description="UUID of the active tenant Organization")] = None
) -> Organization:
    """
    FastAPI dependency resolving the active organization tenant boundary.
    Validates that:
    1. X-Organization-ID header is provided.
    2. The organization exists in the database.
    3. The authenticated user holds a membership in the organization.
    """
    import uuid
    if not x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Organization-ID header missing"
        )
    try:
        org_uuid = uuid.UUID(x_organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Organization-ID header format"
        )

    # Query membership locally to avoid circular dependencies
    from sqlalchemy import select
    from app.organizations.models import Membership, Organization

    statement = select(Membership).where(
        Membership.user_id == current_user.id,
        Membership.organization_id == org_uuid
    )
    result = await db.execute(statement)
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )

    org_statement = select(Organization).where(Organization.id == org_uuid)
    org_result = await db.execute(org_statement)
    org = org_result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org



ActiveOrganizationDep = Annotated[Organization, Depends(get_active_organization)]
