import pytest
from httpx import AsyncClient

from tests.conftest import auth_header


pytestmark = pytest.mark.asyncio


async def test_create_group(client: AsyncClient, admin_token: str):
    """POST /api/v1/groups/ creates a group and returns 201."""
    response = await client.post(
        "/api/v1/groups/",
        json={"name": "Network Team", "description": "Handles network issues"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Network Team"
    assert data["description"] == "Handles network issues"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_list_groups(client: AsyncClient, admin_token: str):
    """GET /api/v1/groups/ returns a list of groups."""
    # Create a group first
    await client.post(
        "/api/v1/groups/",
        json={"name": "Desktop Support", "description": "Desktop team"},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        "/api/v1/groups/",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1
    assert data["items"][0]["name"] == "Desktop Support"


async def test_get_group_detail(client: AsyncClient, admin_token: str):
    """GET /api/v1/groups/{group_id} returns group with members list."""
    # Create a group
    create_response = await client.post(
        "/api/v1/groups/",
        json={"name": "Server Team", "description": "Server ops"},
        headers=auth_header(admin_token),
    )
    group_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/groups/{group_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == group_id
    assert data["name"] == "Server Team"
    assert "members" in data
    assert isinstance(data["members"], list)


async def test_add_member_to_group(
    client: AsyncClient, admin_token: str, agent_user
):
    """POST /api/v1/groups/{group_id}/members adds a user and returns 201."""
    # Create a group
    create_response = await client.post(
        "/api/v1/groups/",
        json={"name": "Security Team", "description": "InfoSec"},
        headers=auth_header(admin_token),
    )
    group_id = create_response.json()["id"]

    # Add agent_user as a member
    response = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": str(agent_user.id), "is_lead": False},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    data = response.json()
    assert data["is_lead"] is False
    assert data["user_id"] == str(agent_user.id)
    assert "joined_at" in data


async def test_remove_member_from_group(
    client: AsyncClient, admin_token: str, agent_user
):
    """DELETE /api/v1/groups/{group_id}/members/{user_id} removes the member and returns 204."""
    # Create a group
    create_response = await client.post(
        "/api/v1/groups/",
        json={"name": "Cloud Team", "description": "Cloud ops"},
        headers=auth_header(admin_token),
    )
    group_id = create_response.json()["id"]

    # Add member
    await client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"user_id": str(agent_user.id), "is_lead": False},
        headers=auth_header(admin_token),
    )

    # Remove member
    response = await client.delete(
        f"/api/v1/groups/{group_id}/members/{agent_user.id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 204


async def test_add_duplicate_member(
    client: AsyncClient, admin_token: str, agent_user
):
    """Adding the same user to a group twice returns 409."""
    # Create a group
    create_response = await client.post(
        "/api/v1/groups/",
        json={"name": "DBA Team", "description": "Database admins"},
        headers=auth_header(admin_token),
    )
    group_id = create_response.json()["id"]

    member_payload = {"user_id": str(agent_user.id), "is_lead": False}

    # First add — should succeed
    first_response = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json=member_payload,
        headers=auth_header(admin_token),
    )
    assert first_response.status_code == 201

    # Second add — should conflict
    second_response = await client.post(
        f"/api/v1/groups/{group_id}/members",
        json=member_payload,
        headers=auth_header(admin_token),
    )
    assert second_response.status_code == 409
