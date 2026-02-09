import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


pytestmark = pytest.mark.asyncio


async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    """Admin can create a new user via POST /api/v1/users/."""
    response = await client.post(
        "/api/v1/users/",
        json={
            "username": "newuser",
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "newuserpass",
            "role": "agent",
        },
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "agent"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_user_as_agent_forbidden(client: AsyncClient, agent_token: str):
    """Agent role cannot create users — expects 403."""
    response = await client.post(
        "/api/v1/users/",
        json={
            "username": "sneakyuser",
            "email": "sneaky@test.com",
            "full_name": "Sneaky User",
            "password": "sneakypass",
            "role": "agent",
        },
        headers=auth_header(agent_token),
    )
    assert response.status_code == 403


async def test_list_users(client: AsyncClient, admin_token: str, admin_user):
    """GET /api/v1/users/ returns paginated response with at least the admin user."""
    response = await client.get(
        "/api/v1/users/",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_get_user_by_id(client: AsyncClient, admin_token: str, admin_user):
    """GET /api/v1/users/{user_id} returns the user detail."""
    user_id = str(admin_user.id)
    response = await client.get(
        f"/api/v1/users/{user_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == user_id
    assert data["username"] == "testadmin"
    assert data["email"] == "testadmin@test.com"


async def test_update_user(client: AsyncClient, admin_token: str, agent_user):
    """Admin can update a user's email via PATCH /api/v1/users/{user_id}."""
    user_id = str(agent_user.id)
    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"email": "updated@test.com"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "updated@test.com"
    assert data["id"] == user_id


async def test_change_own_password(client: AsyncClient, agent_token: str):
    """User can change their own password and log in with the new one."""
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "agentpass", "new_password": "newagentpass"},
        headers=auth_header(agent_token),
    )
    assert response.status_code == 204

    # Verify login with new password works
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testagent", "password": "newagentpass"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_change_password_wrong_current(client: AsyncClient, agent_token: str):
    """Changing password with wrong current password returns 400."""
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "wrongpass", "new_password": "newagentpass"},
        headers=auth_header(agent_token),
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


async def test_change_password_too_short(client: AsyncClient, agent_token: str):
    """Changing password with too-short new password returns 422."""
    response = await client.post(
        "/api/v1/users/me/password",
        json={"current_password": "agentpass", "new_password": "abc"},
        headers=auth_header(agent_token),
    )
    assert response.status_code == 422


async def test_admin_reset_password(
    client: AsyncClient, admin_token: str, agent_user
):
    """Admin can reset a user's password via PATCH with password field."""
    user_id = str(agent_user.id)
    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"password": "resetpass"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    # Verify login with new password works
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testagent", "password": "resetpass"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
