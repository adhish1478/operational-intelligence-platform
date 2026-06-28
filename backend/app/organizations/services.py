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
        # TODO: Implement organization lookup by ID
        # Example:
        # statement = select(Organization).where(Organization.id == org_id)
        # result = await db.execute(statement)
        # return result.scalar_one_or_none()
        raise NotImplementedError("Implement get_organization_by_id in organizations/services.py")

    @staticmethod
    async def get_organization_by_slug(db: AsyncSession, slug: str) -> Organization | None:
        """
        Retrieve an organization profile by its unique slug.
        """
        # TODO: Implement organization lookup by slug
        # Example:
        # statement = select(Organization).where(Organization.slug == slug)
        # result = await db.execute(statement)
        # return result.scalar_one_or_none()
        raise NotImplementedError("Implement get_organization_by_slug in organizations/services.py")

    @staticmethod
    async def list_user_organizations(db: AsyncSession, user_id: uuid.UUID) -> Sequence[Organization]:
        """
        List all organizations that a specific user belongs to.
        """
        # TODO: Implement query listing user organizations
        # Example query using join:
        # statement = select(Organization).join(Membership).where(Membership.user_id == user_id)
        # result = await db.execute(statement)
        # return result.scalars().all()
        raise NotImplementedError("Implement list_user_organizations in organizations/services.py")

    @staticmethod
    async def create_organization(
        db: AsyncSession, org_in: OrganizationCreate, creator_id: uuid.UUID
    ) -> Organization:
        """
        Create a new Organization and automatically insert a Membership record
        linking the creator as the 'owner' of the Organization.
        """
        # TODO: Implement transaction block:
        # 1. Verify slug uniqueness
        # 2. Instantiate and add Organization
        # 3. Instantiate and add Membership (user_id=creator_id, role="owner")
        # 4. Commit and return Organization
        raise NotImplementedError("Implement create_organization in organizations/services.py")

    @staticmethod
    async def add_organization_member(
        db: AsyncSession, org_id: uuid.UUID, member_in: MembershipCreate
    ) -> Membership:
        """
        Add a user to an organization with a specific role.
        """
        # TODO: Implement membership insertion
        raise NotImplementedError("Implement add_organization_member in organizations/services.py")

    @staticmethod
    async def update_member_role(
        db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, role_update: MembershipUpdate
    ) -> Membership:
        """
        Update a member's role (RBAC modification).
        """
        # TODO: Fetch membership and update role
        raise NotImplementedError("Implement update_member_role in organizations/services.py")

    @staticmethod
    async def remove_member(
        db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """
        Remove a user from an organization.
        """
        # TODO: Delete membership record
        raise NotImplementedError("Implement remove_member in organizations/services.py")
