from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.auth.models import User
from app.auth.schemas import UserCreate
from app.core.security import hash_password, verify_password


class AuthService:
    """
    Service layer for managing user registration, retrieval, and auth lifecycles.
    All database transactions are executed asynchronously using SQLAlchemy 2.0.
    """

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """
        Query database for a user matching the provided email address.
        """
        statement = select(User).where(User.email == email)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
        """
        Query database for a user matching the provided unique ID.
        """
        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
        """
        Create a new user record inside PostgreSQL after password hashing.
        Raises ValueError if the email is already registered.
        """
        existing_user = await AuthService.get_user_by_email(db, user_in.email)
        if existing_user is not None:
            raise ValueError("User with this email already exists")

        user = User(
            email=str(user_in.email).lower().strip(),
            password_hash=hash_password(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user_profile(db: AsyncSession, user: User, first_name: str | None, last_name: str | None) -> User:
        """
        Update user profile first_name and last_name in PostgreSQL.
        """
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
