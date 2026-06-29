import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from app.organizations.models import Organization, Membership
from app.organizations.schemas import OrganizationCreate, MembershipCreate, MembershipUpdate


class OrganizationService:
    """
    Service layer mapping Database transactions for Organizations and Memberships.
    All functions are asynchronous and use SQLAlchemy 2.0.
    """

    @staticmethod
    async def get_organization_by_id(db: AsyncSession, org_id: uuid.UUID) -> Organization | None:
        """
        Retrieve an organization profile by its unique ID.
        """
        from sqlalchemy import select
        statement = select(Organization).where(Organization.id == org_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_organization_by_slug(db: AsyncSession, slug: str) -> Organization | None:
        """
        Retrieve an organization profile by its unique slug.
        """
        from sqlalchemy import select
        statement = select(Organization).where(Organization.slug == slug)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_organizations(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Organization]:
        """
        List all organizations that a specific user belongs to.
        """
        from sqlalchemy import select
        statement = select(Organization).join(Membership).where(Membership.user_id == user_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def create_organization(
        db: AsyncSession, org_in: OrganizationCreate, creator_id: uuid.UUID
    ) -> Organization:
        """
        Create a new Organization and automatically insert a Membership record
        linking the creator as the 'owner' of the Organization.
        """
        # 1. Verify slug uniqueness
        existing_org = await OrganizationService.get_organization_by_slug(db, org_in.slug)
        if existing_org is not None:
            raise ValueError("Organization with this slug already exists")

        # 2. Instantiate and add Organization
        org = Organization(
            name=org_in.name,
            slug=org_in.slug.lower().strip()
        )
        db.add(org)
        await db.flush()  # Populates org.id

        # 3. Instantiate and add Membership (user_id=creator_id, role="owner")
        membership = Membership(
            user_id=creator_id,
            organization_id=org.id,
            role="owner"
        )
        db.add(membership)
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def add_organization_member(
        db: AsyncSession, org_id: uuid.UUID, member_in: MembershipCreate
    ) -> Membership:
        """
        Add a user to an organization with a specific role.
        """
        from sqlalchemy import select
        # Check if membership already exists
        statement = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == member_in.user_id
        )
        result = await db.execute(statement)
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise ValueError("User is already a member of this organization")

        membership = Membership(
            user_id=member_in.user_id,
            organization_id=org_id,
            role=member_in.role
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)
        return membership

    @staticmethod
    async def update_member_role(
        db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, role_update: MembershipUpdate
    ) -> Membership:
        """
        Update a member's role (RBAC modification).
        """
        from sqlalchemy import select
        # Fetch membership
        statement = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id
        )
        result = await db.execute(statement)
        membership = result.scalar_one_or_none()
        if membership is None:
            raise ValueError("Membership record not found")

        membership.role = role_update.role
        db.add(membership)
        await db.commit()
        await db.refresh(membership)
        return membership

    @staticmethod
    async def remove_member(
        db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """
        Remove a user from an organization.
        """
        from sqlalchemy import select
        # Fetch membership
        statement = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id
        )
        result = await db.execute(statement)
        membership = result.scalar_one_or_none()
        if membership is None:
            raise ValueError("Membership record not found")

        await db.delete(membership)
        await db.commit()

