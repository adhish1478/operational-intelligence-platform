import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.core.security import hash_password

# All tests in this module are async and use pytest-asyncio
pytestmark = pytest.mark.asyncio


async def test_register_user_success(client: AsyncClient):
    """Test successful user registration."""
    payload = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "first_name": "John",
        "last_name": "Doe"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert "id" in data
    assert "password" not in data


async def test_register_duplicate_user(client: AsyncClient, db_session: AsyncSession):
    """Test duplicate registration returns 400 Bad Request."""
    # Pre-populate database with a user
    user = User(
        email="duplicate@example.com",
        password_hash=hash_password("password123"),
        first_name="Jane",
        last_name="Smith"
    )
    db_session.add(user)
    await db_session.commit()

    payload = {
        "email": "duplicate@example.com",
        "password": "newpassword123",
        "first_name": "Jane",
        "last_name": "Smith"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login returns access token and sets refresh token cookie."""
    user = User(
        email="testlogin@example.com",
        password_hash=hash_password("mypassword123"),
        first_name="Login",
        last_name="Test"
    )
    db_session.add(user)
    await db_session.commit()

    payload = {
        "email": "testlogin@example.com",
        "password": "mypassword123"
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Assert HttpOnly refresh token cookie is set
    assert "refresh_token" in response.cookies
    # We can fetch cookie metadata from client.cookies jar if needed
    cookie = response.history[0].headers.get("set-cookie") if response.history else response.headers.get("set-cookie")
    assert "HttpOnly" in cookie


async def test_login_incorrect_credentials(client: AsyncClient, db_session: AsyncSession):
    """Test login fails with invalid credentials."""
    user = User(
        email="testfail@example.com",
        password_hash=hash_password("mypassword123")
    )
    db_session.add(user)
    await db_session.commit()

    # Wrong password
    response = await client.post("/api/v1/auth/login", json={
        "email": "testfail@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    
    # Non-existent email
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "password123"
    })
    assert response.status_code == 401


async def test_get_me_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting current user profile with valid authorization token."""
    user = User(
        email="testme@example.com",
        password_hash=hash_password("password123"),
        first_name="Me",
        last_name="Myself"
    )
    db_session.add(user)
    await db_session.commit()

    # Login to get token
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "testme@example.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]

    # Fetch profile
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == "testme@example.com"
    assert data["first_name"] == "Me"


async def test_get_me_unauthorized(client: AsyncClient):
    """Test /me endpoint rejects requests without credentials or invalid token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

    headers = {"Authorization": "Bearer invalidtoken"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


async def test_refresh_token_rotation(client: AsyncClient, db_session: AsyncSession):
    """Test refresh token endpoints rotates refresh tokens and yields new access token."""
    user = User(
        email="testrefresh@example.com",
        password_hash=hash_password("password123")
    )
    db_session.add(user)
    await db_session.commit()

    # Login to establish cookie
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "testrefresh@example.com",
        "password": "password123"
    })
    
    # Assert client holds the cookie
    assert "refresh_token" in client.cookies

    # Call refresh endpoint (it automatically sends the cookies stored in the client)
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in client.cookies


async def test_logout_success(client: AsyncClient, db_session: AsyncSession):
    """Test logout clears the refresh token cookie."""
    user = User(
        email="testlogout@example.com",
        password_hash=hash_password("password123")
    )
    db_session.add(user)
    await db_session.commit()

    # Login
    await client.post("/api/v1/auth/login", json={
        "email": "testlogout@example.com",
        "password": "password123"
    })
    assert "refresh_token" in client.cookies

    # Logout
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    
    # Assert refresh token cookie is removed/expired from client jar
    assert "refresh_token" not in client.cookies
