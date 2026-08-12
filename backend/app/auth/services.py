import uuid
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.auth.models import User
from app.auth.schemas import UserCreate, OrganizationRef, ProfileUpdatePayload
from app.organizations.models import Organization, Membership
from app.core.security import hash_password, verify_password


class AuthService:
    """
    Service layer for managing user registration, retrieval, and auth lifecycles.
    All database transactions are executed asynchronously using SQLAlchemy 2.0.
    """

    @staticmethod
    async def populate_user_organizations(db: AsyncSession, user: User) -> User:
        """
        Fetch user's memberships and organizations, attaching an `organizations` list to the User object.
        """
        if not user or not hasattr(user, "id"):
            return user

        try:
            stmt = (
                select(Membership)
                .options(selectinload(Membership.organization))
                .where(Membership.user_id == user.id)
            )
            res = await db.execute(stmt)
            memberships = res.scalars().all()
            
            org_refs = []
            for m in memberships:
                if m and m.organization:
                    org_refs.append(
                        OrganizationRef(
                            id=m.organization.id,
                            name=m.organization.name,
                            slug=m.organization.slug,
                            role=m.role or "member"
                        )
                    )
            setattr(user, "organizations", org_refs)
        except Exception as e:
            print(f"⚠️ Could not populate user organizations: {e}")
            setattr(user, "organizations", [])

        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """
        Query database for a user matching the provided email address.
        """
        statement = select(User).where(User.email == email)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        if user:
            await AuthService.populate_user_organizations(db, user)
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str | uuid.UUID) -> User | None:
        """
        Query database for a user matching the provided unique ID.
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        if user:
            await AuthService.populate_user_organizations(db, user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
        """
        Authenticate user credentials by email and password.
        """
        user = await AuthService.get_user_by_email(db, email.lower().strip())
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    async def register_user(db: AsyncSession, user_in: UserCreate) -> User:
        """
        Create a new user record inside PostgreSQL after password hashing.
        Automatically creates an Organization and Membership if organization_name is provided.
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

        # Create default Organization and Membership for new user
        org_name = (user_in.organization_name or "").strip()
        if not org_name:
            fn = (user_in.first_name or "My").strip()
            org_name = f"{fn}'s Organization"

        base_slug = re.sub(r'[^a-z0-9\s-]', '', org_name.lower()).replace(' ', '-').strip('-') or "org"
        slug = f"{base_slug}-{str(uuid.uuid4())[:6]}"

        new_org = Organization(name=org_name, slug=slug)
        db.add(new_org)
        await db.commit()
        await db.refresh(new_org)

        new_membership = Membership(
            user_id=user.id,
            organization_id=new_org.id,
            role="Admin"
        )
        db.add(new_membership)
        await db.commit()

        await AuthService.populate_user_organizations(db, user)
        return user

    @staticmethod
    async def update_user_profile(
        db: AsyncSession, 
        user: User, 
        payload: ProfileUpdatePayload
    ) -> User:
        """
        Update user profile first_name, last_name, email, and role in PostgreSQL.
        """
        if payload.full_name is not None and payload.full_name.strip():
            parts = payload.full_name.strip().split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
        else:
            if payload.first_name is not None:
                user.first_name = payload.first_name.strip()
            if payload.last_name is not None:
                user.last_name = payload.last_name.strip()

        if payload.email is not None and payload.email.lower().strip() != user.email:
            new_email = payload.email.lower().strip()
            existing = await AuthService.get_user_by_email(db, new_email)
            if existing and existing.id != user.id:
                raise ValueError("An account with this email address already exists")
            user.email = new_email

        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Update role in active membership if role is provided
        if payload.role is not None and payload.role.strip():
            stmt = select(Membership).where(Membership.user_id == user.id)
            res = await db.execute(stmt)
            membership = res.scalars().first()
            if membership:
                membership.role = payload.role.strip()
                db.add(membership)
                await db.commit()

        await AuthService.populate_user_organizations(db, user)
        return user
