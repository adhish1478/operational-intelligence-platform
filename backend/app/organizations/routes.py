import uuid
from typing import Any
from fastapi import APIRouter, status, Depends, HTTPException
from app.api.deps import DBSessionDep, CurrentUserDep
from app.organizations.schemas import (
    OrganizationCreate,
    OrganizationRead,
    MembershipRead,
    MembershipCreate,
    MembershipUpdate
)
from app.organizations.services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "/",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED
)
async def create_new_organization(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_in: OrganizationCreate
) -> Any:
    """
    Create a new organization workspace.
    The calling user is automatically registered as the Organization Owner.
    """
    try:
        org = await OrganizationService.create_organization(db, org_in, current_user.id)
        return org
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=list[OrganizationRead]
)
async def list_my_organizations(
    db: DBSessionDep,
    current_user: CurrentUserDep
) -> Any:
    """
    List all organizations the currently authenticated user belongs to.
    """
    orgs = await OrganizationService.list_user_organizations(db, current_user.id)
    return orgs


@router.get(
    "/{org_id}",
    response_model=OrganizationRead
)
async def get_org_details(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_id: uuid.UUID
) -> Any:
    """
    Retrieve details of a specific organization by ID.
    Enforces that the calling user must be a member of the organization.
    """
    from sqlalchemy import select
    from app.organizations.models import Membership
    statement = select(Membership).where(
        Membership.organization_id == org_id,
        Membership.user_id == current_user.id
    )
    result = await db.execute(statement)
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )

    org = await OrganizationService.get_organization_by_id(db, org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org


@router.post(
    "/{org_id}/members",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED
)
async def invite_member(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_id: uuid.UUID,
    member_in: MembershipCreate
) -> Any:
    """
    Invite / add a new user to the organization with a specific role.
    Enforces admin/owner role boundaries for the requester.
    """
    from sqlalchemy import select
    from app.organizations.models import Membership
    statement = select(Membership).where(
        Membership.organization_id == org_id,
        Membership.user_id == current_user.id
    )
    result = await db.execute(statement)
    requester_membership = result.scalar_one_or_none()
    if not requester_membership or requester_membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can invite members"
        )

    try:
        membership = await OrganizationService.add_organization_member(db, org_id, member_in)
        return membership
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch(
    "/{org_id}/members/{user_id}",
    response_model=MembershipRead
)
async def modify_member_role(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role_update: MembershipUpdate
) -> Any:
    """
    Modify a user's role membership within the organization boundary.
    Enforces administrative permissions.
    """
    from sqlalchemy import select
    from app.organizations.models import Membership
    statement = select(Membership).where(
        Membership.organization_id == org_id,
        Membership.user_id == current_user.id
    )
    result = await db.execute(statement)
    requester_membership = result.scalar_one_or_none()
    if not requester_membership or requester_membership.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can modify member roles"
        )

    try:
        membership = await OrganizationService.update_member_role(db, org_id, user_id, role_update)
        return membership
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_org_member(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_id: uuid.UUID,
    user_id: uuid.UUID
) -> None:
    """
    Remove a member from the organization.
    Enforces administrative boundaries or self-removal.
    """
    if current_user.id != user_id:
        from sqlalchemy import select
        from app.organizations.models import Membership
        statement = select(Membership).where(
            Membership.organization_id == org_id,
            Membership.user_id == current_user.id
        )
        result = await db.execute(statement)
        requester_membership = result.scalar_one_or_none()
        if not requester_membership or requester_membership.role not in ["owner", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners and admins can remove members"
            )

    try:
        await OrganizationService.remove_member(db, org_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{org_id}/members",
    response_model=list[MembershipRead]
)
async def list_org_members(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    org_id: uuid.UUID
) -> Any:
    """
    List all members in the organization.
    Enforces that the calling user must be a member of the organization.
    """
    from sqlalchemy import select
    from app.organizations.models import Membership
    statement = select(Membership).where(
        Membership.organization_id == org_id,
        Membership.user_id == current_user.id
    )
    result = await db.execute(statement)
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )

    members = await OrganizationService.list_organization_members(db, org_id)
    return members


