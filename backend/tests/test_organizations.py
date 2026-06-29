import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.organizations.models import Organization, Membership
from app.core.security import hash_password
from app.main import app
from app.api.deps import ActiveOrganizationDep
from app.organizations.schemas import OrganizationRead

# All tests in this module are async and use pytest-asyncio
pytestmark = pytest.mark.asyncio


# Define a temporary endpoint on the FastAPI app to directly test the ActiveOrganizationDep header injection
@app.get("/api/v1/test-org-dep-boundary", response_model=OrganizationRead, tags=["test"])
async def get_test_org_dep_boundary(org: ActiveOrganizationDep):
    return org


async def test_create_organization_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful organization creation."""
    # Create user
    user = User(
        email="orgcreator@example.com",
        password_hash=hash_password("password123")
    )
    db_session.add(user)
    await db_session.commit()

    # Login to get token
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "orgcreator@example.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Acme Corporation",
        "slug": "acme"
    }
    response = await client.post("/api/v1/organizations/", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corporation"
    assert data["slug"] == "acme"
    assert "id" in data

    # Verify that the user is now the owner of the organization
    from sqlalchemy import select
    statement = select(Membership).where(
        Membership.organization_id == uuid.UUID(data["id"]),
        Membership.user_id == user.id
    )
    result = await db_session.execute(statement)
    membership = result.scalar_one_or_none()
    assert membership is not None
    assert membership.role == "owner"


async def test_create_organization_duplicate_slug(client: AsyncClient, db_session: AsyncSession):
    """Test creating an organization with a duplicate slug returns 400 Bad Request."""
    user = User(
        email="creator2@example.com",
        password_hash=hash_password("password123")
    )
    db_session.add(user)
    await db_session.commit()

    # Create pre-existing org
    org = Organization(name="Original Inc", slug="original")
    db_session.add(org)
    await db_session.flush()
    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "creator2@example.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Duplicate slug
    payload = {
        "name": "Different Name",
        "slug": "original"
    }
    response = await client.post("/api/v1/organizations/", json=payload, headers=headers)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


async def test_list_my_organizations(client: AsyncClient, db_session: AsyncSession):
    """Test listing only organizations that the user belongs to."""
    user1 = User(email="user1@example.com", password_hash=hash_password("password"))
    user2 = User(email="user2@example.com", password_hash=hash_password("password"))
    db_session.add_all([user1, user2])
    await db_session.commit()

    org1 = Organization(name="Org 1", slug="org-1")
    org2 = Organization(name="Org 2", slug="org-2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    # user 1 belongs to org1
    # user 2 belongs to org2
    db_session.add(Membership(user_id=user1.id, organization_id=org1.id, role="member"))
    db_session.add(Membership(user_id=user2.id, organization_id=org2.id, role="member"))
    await db_session.commit()

    # Login user 1
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "user1@example.com",
        "password": "password"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/organizations/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slug"] == "org-1"


async def test_get_org_details_membership_check(client: AsyncClient, db_session: AsyncSession):
    """Test fetching org details checks memberships strictly."""
    user1 = User(email="u1@example.com", password_hash=hash_password("password"))
    user2 = User(email="u2@example.com", password_hash=hash_password("password"))
    db_session.add_all([user1, user2])
    await db_session.commit()

    org = Organization(name="Secret Org", slug="secret")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user1.id, organization_id=org.id, role="owner"))
    await db_session.commit()

    # Login user 2 (non-member)
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "u2@example.com",
        "password": "password"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/organizations/{org.id}", headers=headers)
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]

    # Login user 1 (member)
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "u1@example.com",
        "password": "password"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/organizations/{org.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["slug"] == "secret"


async def test_invite_member_rbac(client: AsyncClient, db_session: AsyncSession):
    """Test that only owner/admin roles can invite new members."""
    admin_user = User(email="admin@example.com", password_hash=hash_password("pass"))
    regular_user = User(email="regular@example.com", password_hash=hash_password("pass"))
    target_user = User(email="target@example.com", password_hash=hash_password("pass"))
    db_session.add_all([admin_user, regular_user, target_user])
    await db_session.commit()

    org = Organization(name="Initech", slug="initech")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=admin_user.id, organization_id=org.id, role="admin"))
    db_session.add(Membership(user_id=regular_user.id, organization_id=org.id, role="member"))
    await db_session.commit()

    # Login regular member
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "regular@example.com",
        "password": "pass"
    })
    token_regular = login_resp.json()["access_token"]

    # Regular member tries to invite target user -> Should fail with 403
    payload = {
        "user_id": str(target_user.id),
        "role": "member"
    }
    response = await client.post(
        f"/api/v1/organizations/{org.id}/members",
        json=payload,
        headers={"Authorization": f"Bearer {token_regular}"}
    )
    assert response.status_code == 403

    # Login admin user
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "pass"
    })
    token_admin = login_resp.json()["access_token"]

    # Admin invites target user -> Success
    response = await client.post(
        f"/api/v1/organizations/{org.id}/members",
        json=payload,
        headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == str(target_user.id)


async def test_modify_member_role(client: AsyncClient, db_session: AsyncSession):
    """Test modifying membership roles."""
    owner_user = User(email="owner@org.com", password_hash=hash_password("pwd"))
    target_user = User(email="target@org.com", password_hash=hash_password("pwd"))
    db_session.add_all([owner_user, target_user])
    await db_session.commit()

    org = Organization(name="Roles Inc", slug="roles")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=owner_user.id, organization_id=org.id, role="owner"))
    target_membership = Membership(user_id=target_user.id, organization_id=org.id, role="member")
    db_session.add(target_membership)
    await db_session.commit()

    # Login owner
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "owner@org.com",
        "password": "pwd"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Promote user to admin
    response = await client.patch(
        f"/api/v1/organizations/{org.id}/members/{target_user.id}",
        json={"role": "admin"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_remove_member_self_vs_others(client: AsyncClient, db_session: AsyncSession):
    """Test removing members (admin removes regular user, regular user removes themselves)."""
    admin_user = User(email="adm@org.com", password_hash=hash_password("pwd"))
    member_user = User(email="mem@org.com", password_hash=hash_password("pwd"))
    db_session.add_all([admin_user, member_user])
    await db_session.commit()

    org = Organization(name="Goodbye Inc", slug="goodbye")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=admin_user.id, organization_id=org.id, role="admin"))
    db_session.add(Membership(user_id=member_user.id, organization_id=org.id, role="member"))
    await db_session.commit()

    # 1. Login regular member
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "mem@org.com",
        "password": "pwd"
    })
    token_member = login_resp.json()["access_token"]

    # Member tries to remove admin -> Should fail
    response = await client.delete(
        f"/api/v1/organizations/{org.id}/members/{admin_user.id}",
        headers={"Authorization": f"Bearer {token_member}"}
    )
    assert response.status_code == 403

    # Member removes themselves -> Success (204 No Content)
    response = await client.delete(
        f"/api/v1/organizations/{org.id}/members/{member_user.id}",
        headers={"Authorization": f"Bearer {token_member}"}
    )
    assert response.status_code == 204


async def test_active_org_dependency_injection(client: AsyncClient, db_session: AsyncSession):
    """Test that ActiveOrganizationDep correctly validates header X-Organization-ID."""
    user = User(email="dep@test.com", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    org = Organization(name="Dependency Testing", slug="dep-test")
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(user_id=user.id, organization_id=org.id, role="member"))
    await db_session.commit()

    # Login
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "dep@test.com",
        "password": "pass"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Missing header -> 400 Bad Request
    response = await client.get("/api/v1/test-org-dep-boundary", headers=headers)
    assert response.status_code == 400
    assert "header missing" in response.json()["detail"]

    # 2. Invalid UUID format -> 400 Bad Request
    bad_headers = {**headers, "X-Organization-ID": "invalid-uuid-format"}
    response = await client.get("/api/v1/test-org-dep-boundary", headers=bad_headers)
    assert response.status_code == 400
    assert "Invalid X-Organization-ID header format" in response.json()["detail"]

    # 3. Not a member of the organization (using random UUID)
    random_uuid = str(uuid.uuid4())
    random_headers = {**headers, "X-Organization-ID": random_uuid}
    response = await client.get("/api/v1/test-org-dep-boundary", headers=random_headers)
    assert response.status_code == 403
    assert "not a member" in response.json()["detail"]

    # 4. Valid member and correct header -> Success
    valid_headers = {**headers, "X-Organization-ID": str(org.id)}
    response = await client.get("/api/v1/test-org-dep-boundary", headers=valid_headers)
    assert response.status_code == 200
    assert response.json()["slug"] == "dep-test"
