from typing import Annotated
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.auth.models import User
from app.auth.services import AuthService
from app.organizations.models import Organization

# OAuth2 security scheme for header parsing
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Common Type Aliases for injection clarity
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(db: DBSessionDep, token: TokenDep) -> User:
    """
    FastAPI dependency that extracts, decodes, and validates the incoming JWT access token.
    Returns the User database object if signature is valid, token is unexpired,
    and user exists/is active.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
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
    # TODO: Implement active organization checks
    # Example logic:
    # 1. If not x_organization_id -> raise HTTP 400 Bad Request
    # 2. Parse UUID. If invalid -> raise HTTP 400
    # 3. Query Membership where user_id=current_user.id and organization_id=parsed_uuid
    # 4. If not found -> raise HTTP 403 Forbidden
    # 5. Query Organization by parsed_uuid and return Organization object
    raise NotImplementedError("Implement get_active_organization in api/deps.py")


ActiveOrganizationDep = Annotated[Organization, Depends(get_active_organization)]
