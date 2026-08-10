from datetime import timedelta
import jwt
from fastapi import APIRouter, Response, Request, status, HTTPException
from app.api.deps import DBSessionDep, CurrentUserDep, TokenDep

from app.auth.schemas import UserCreate, UserRead, Token, UserLogin
from app.auth.services import AuthService
from app.core.security import create_token, decode_token
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register", 
    response_model=UserRead, 
    status_code=status.HTTP_201_CREATED
)
async def register(db: DBSessionDep, user_in: UserCreate) -> UserRead:
    """
    Register a new user account on the OIP platform.
    Passwords will be hashed automatically on registration.
    """
    try:
        user = await AuthService.register_user(db, user_in)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
async def login(
    db: DBSessionDep, 
    response: Response, 
    credentials: UserLogin
) -> Token:
    """
    Authenticate user credentials.
    - Access Token is returned in the JSON response payload.
    - Refresh Token is written to an HttpOnly secure cookie.
    """
    user = await AuthService.authenticate_user(
        db, email=credentials.email, password=credentials.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    # Generate Access Token (Standard 15-minute lifespan)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        subject=user.id, expires_delta=access_token_expires, token_type="access"
    )
    
    # Generate Refresh Token
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_token(
        subject=user.id, expires_delta=refresh_token_expires, token_type="refresh"
    )
    
    # Set HttpOnly Refresh Token Cookie
    # In production, enforce secure=True; in development, set secure=False if using plain HTTP
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="none",
        secure=True,
    )
    
    return Token(access_token=access_token)


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    db: DBSessionDep, 
    request: Request, 
    response: Response
) -> Token:
    """
    Issue a fresh Access Token using the valid Refresh Token stored in cookies.
    Implements Refresh Token Rotation.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh credentials"
    )
    
    try:
        payload = decode_token(refresh_token)
        token_type = payload.get("type")
        if token_type != "refresh":
            raise credentials_exception
            
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise credentials_exception
        
    user = await AuthService.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception
        
    # Refresh Token Rotation: Issue a new pair
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_token(
        subject=user.id, expires_delta=access_token_expires, token_type="access"
    )
    
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = create_token(
        subject=user.id, expires_delta=refresh_token_expires, token_type="refresh"
    )
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        samesite="none",
        secure=True,
    )
    
    return Token(access_token=new_access_token)


@router.get("/me", response_model=UserRead)
async def get_current_profile(current_user: CurrentUserDep) -> UserRead:
    """
    Retrieve authentication details of the currently authenticated active user.
    Uses the CurrentUserDep dependency to validate the Access Token.
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    token: TokenDep
) -> dict[str, str]:
    """
    Invalidate client authorization by blocklisting the Access Token and clearing the Refresh Token cookie.
    """
    from app.auth.blocklist import blocklist_token
    blocklist_token(token)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="none",
        secure=True,
    )
    return {"message": "Logged out successfully"}

