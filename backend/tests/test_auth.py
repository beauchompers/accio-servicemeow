import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


pytestmark = pytest.mark.asyncio


async def test_login_valid_credentials(client: AsyncClient, admin_user):
    """POST /api/v1/auth/login with correct credentials returns 200 and tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # The refresh token should be set as an HTTP-only cookie
    assert "refresh_token" in response.cookies


async def test_login_invalid_password(client: AsyncClient, admin_user):
    """POST /api/v1/auth/login with wrong password returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    """POST /api/v1/auth/login with unknown username returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "whatever"},
    )
    assert response.status_code == 401


async def test_refresh_valid_cookie(client: AsyncClient, admin_user):
    """Login first, then POST /api/v1/auth/refresh with the cookie to get a new access token."""
    # Step 1: Login to get the refresh token cookie
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "adminpass"},
    )
    assert login_response.status_code == 200

    # Step 2: Use the refresh cookie to get a new access token.
    # The cookie is set with secure=True, so we must forward it explicitly
    # since the test client uses http:// not https://.
    refresh_token = login_response.cookies.get("refresh_token")
    assert refresh_token is not None
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200

    data = refresh_response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_protected_route_no_auth(client: AsyncClient):
    """GET /api/v1/users without a token returns 401."""
    response = await client.get("/api/v1/users/")
    assert response.status_code == 401
