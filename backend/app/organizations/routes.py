import uuid
from typing import Any
from fastapi import APIRouter, status, Depends
from app.api.deps import DBSessionDep, CurrentUserDep
from app.organizations.schemas import (
    OrganizationCreate,
    OrganizationRead,
    MembershipRead,
    MembershipCreate,
    MembershipUpdate
)

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
    # TODO: Invoke OrganizationService.create_organization
    raise NotImplementedError("Implement create_new_organization in organizations/routes.py")


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
    # TODO: Invoke OrganizationService.list_user_organizations
    raise NotImplementedError("Implement list_my_organizations in organizations/routes.py")


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
    # TODO: Retrieve organization and check user memberships
    raise NotImplementedError("Implement get_org_details in organizations/routes.py")


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
    # TODO: Add member using OrganizationService.add_organization_member
    raise NotImplementedError("Implement invite_member in organizations/routes.py")


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
    # TODO: Invoke OrganizationService.update_member_role
    raise NotImplementedError("Implement modify_member_role in organizations/routes.py")


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
    # TODO: Invoke OrganizationService.remove_member
    raise NotImplementedError("Implement remove_org_member in organizations/routes.py")
