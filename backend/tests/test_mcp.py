import json
import pytest
from httpx import AsyncClient

from app.models.group import Group, GroupMembership
from tests.conftest import auth_header

pytestmark = pytest.mark.asyncio


async def _create_api_key(client: AsyncClient, admin_token: str) -> str:
    """Helper to create an API key and return the plain key."""
    response = await client.post(
        "/api/v1/api-keys/",
        json={"name": "Test MCP Key"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    return response.json()["plain_key"]


async def _mcp_call(
    client: AsyncClient,
    method: str,
    params: dict | None = None,
    api_key: str | None = None,
) -> dict:
    """Helper to make an MCP JSON-RPC call and parse the response.

    Sends the api_key as an HTTP header (not as a tool argument).
    Asserts HTTP 200 and returns the parsed JSON-RPC response.
    """
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        payload["params"] = params
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Host": "localhost",
    }
    if api_key:
        headers["api_key"] = api_key
    response = await client.post("/mcp/", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    return data


# ---------------------------------------------------------------------------
# Tool Discovery
# ---------------------------------------------------------------------------


async def test_mcp_list_tools(client: AsyncClient, admin_token: str):
    """Tool discovery returns all registered tools."""
    result = await _mcp_call(client, "tools/list")
    assert "result" in result
    tools = result["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    # Check key tools are registered
    assert "create_ticket" in tool_names
    assert "get_ticket" in tool_names
    assert "list_tickets" in tool_names
    assert "get_dashboard_summary" in tool_names
    assert "list_groups" in tool_names
    assert "get_system_info" in tool_names
    assert "get_ticket_notes" in tool_names
    assert "get_my_tickets" in tool_names


# ---------------------------------------------------------------------------
# Ticket Tools
# ---------------------------------------------------------------------------


async def test_mcp_create_ticket(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Create a ticket via MCP tool call."""
    api_key = await _create_api_key(client, admin_token)
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "MCP Test Ticket",
                "description": "Created via MCP",
                "priority": "medium",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    assert "result" in result
    content = result["result"]["content"]
    assert len(content) > 0
    tool_result = json.loads(content[0]["text"])
    assert "data" in tool_result
    assert tool_result["data"]["ticket_number"].startswith("ASM-")


async def test_mcp_get_ticket(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Get a ticket by ticket number via MCP."""
    api_key = await _create_api_key(client, admin_token)
    # First create a ticket
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Get Test",
                "description": "desc",
                "priority": "high",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    ticket_number = json.loads(
        create_result["result"]["content"][0]["text"]
    )["data"]["ticket_number"]

    # Get by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "get_ticket",
            "arguments": {"ticket_id_or_number": ticket_number},
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["ticket_number"] == ticket_number
    assert tool_result["data"]["title"] == "Get Test"


async def test_mcp_list_tickets(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """List tickets with filters via MCP."""
    api_key = await _create_api_key(client, admin_token)
    # Create a ticket
    await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "List Test",
                "description": "desc",
                "priority": "low",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    # List
    result = await _mcp_call(
        client,
        "tools/call",
        {"name": "list_tickets", "arguments": {}},
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["total"] >= 1


async def test_mcp_resolve_ticket(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Resolve a ticket with a resolution note via MCP."""
    api_key = await _create_api_key(client, admin_token)
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Resolve Test",
                "description": "desc",
                "priority": "medium",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    ticket_id = json.loads(
        create_result["result"]["content"][0]["text"]
    )["data"]["id"]

    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "resolve_ticket",
            "arguments": {
                "ticket_id_or_number": ticket_id,
                "resolution_note": "Fixed the issue",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["status"] == "resolved"


async def test_mcp_add_note(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Add a note to a ticket via MCP."""
    api_key = await _create_api_key(client, admin_token)
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Note Test",
                "description": "desc",
                "priority": "low",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    ticket_id = json.loads(
        create_result["result"]["content"][0]["text"]
    )["data"]["id"]

    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "add_ticket_note",
            "arguments": {
                "ticket_id_or_number": ticket_id,
                "content": "MCP note content",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["content"] == "MCP note content"


# ---------------------------------------------------------------------------
# Info Tools
# ---------------------------------------------------------------------------


async def test_mcp_dashboard_summary(client: AsyncClient, admin_token: str):
    """Get dashboard summary via MCP."""
    api_key = await _create_api_key(client, admin_token)
    result = await _mcp_call(
        client,
        "tools/call",
        {"name": "get_dashboard_summary", "arguments": {}},
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert "total_tickets" in tool_result["data"]


async def test_mcp_get_system_info(client: AsyncClient, admin_token: str):
    """get_system_info works without authentication and returns enum values."""
    result = await _mcp_call(
        client,
        "tools/call",
        {"name": "get_system_info", "arguments": {}},
    )
    assert "result" in result
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert "data" in tool_result
    data = tool_result["data"]
    assert "statuses" in data
    assert "priorities" in data
    assert "roles" in data
    assert "open" in data["statuses"]
    assert "critical" in data["priorities"]
    assert "admin" in data["roles"]


async def test_mcp_get_ticket_notes(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Create a ticket, add a note, then retrieve notes via get_ticket_notes."""
    api_key = await _create_api_key(client, admin_token)

    # Create ticket
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Notes Retrieval Test",
                "description": "desc",
                "priority": "medium",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    created = json.loads(create_result["result"]["content"][0]["text"])
    ticket_id = created["data"]["id"]
    ticket_number = created["data"]["ticket_number"]

    # Add a note
    await _mcp_call(
        client,
        "tools/call",
        {
            "name": "add_ticket_note",
            "arguments": {
                "ticket_id_or_number": ticket_id,
                "content": "First note for retrieval test",
            },
        },
        api_key=api_key,
    )

    # Retrieve notes by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "get_ticket_notes",
            "arguments": {"ticket_id_or_number": ticket_number},
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert isinstance(tool_result["data"], list)
    assert len(tool_result["data"]) >= 1
    assert tool_result["data"][0]["content"] == "First note for retrieval test"


async def test_mcp_get_my_tickets(
    client: AsyncClient,
    admin_token: str,
    admin_user,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Create a ticket assigned to the admin user, then retrieve via get_my_tickets."""
    api_key = await _create_api_key(client, admin_token)

    # Create ticket assigned to admin user
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "My Ticket Test",
                "description": "assigned to me",
                "priority": "high",
                "assigned_group": str(test_group.id),
                "assigned_user": str(admin_user.id),
            },
        },
        api_key=api_key,
    )
    created = json.loads(create_result["result"]["content"][0]["text"])
    assert created["data"]["ticket_number"].startswith("ASM-")

    # Get my tickets
    result = await _mcp_call(
        client,
        "tools/call",
        {"name": "get_my_tickets", "arguments": {}},
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["total"] >= 1
    ticket_titles = [t["title"] for t in tool_result["data"]["tickets"]]
    assert "My Ticket Test" in ticket_titles


async def test_mcp_name_based_lookup(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Create a ticket using group name instead of UUID (name-based resolver)."""
    api_key = await _create_api_key(client, admin_token)
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Name Lookup Test",
                "description": "using group name",
                "priority": "low",
                "assigned_group": test_group.name,
            },
        },
        api_key=api_key,
    )
    assert "result" in result
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert "data" in tool_result
    assert tool_result["data"]["ticket_number"].startswith("ASM-")


# ---------------------------------------------------------------------------
# Auth Errors
# ---------------------------------------------------------------------------


async def test_mcp_invalid_api_key(client: AsyncClient, admin_token: str):
    """MCP request with invalid API key header returns HTTP 401."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_ticket",
            "arguments": {
                "title": "Bad Key",
                "description": "desc",
                "priority": "low",
                "assigned_group": "00000000-0000-0000-0000-000000000001",
            },
        },
    }
    response = await client.post(
        "/mcp/",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Host": "localhost",
            "api_key": "asm_invalid_key_here_12345678901234567890",
        },
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data


async def test_mcp_no_auth_tool_call(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """Tool call without api_key header reaches the tool and gets a ValueError error response."""
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "No Auth",
                "description": "desc",
                "priority": "low",
                "assigned_group": str(test_group.id),
            },
        },
        # No api_key -- middleware passes through, tool raises ValueError
    )
    content = result["result"]["content"]
    text = content[0]["text"]
    tool_result = json.loads(text)
    assert tool_result["data"] is None
    assert "Authentication required" in tool_result["summary"]


# ---------------------------------------------------------------------------
# MCP Tool Quality Improvements
# ---------------------------------------------------------------------------


async def test_get_ticket_notes_singular_grammar(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """get_ticket_notes says 'Found 1 note' (not 'notes') for a single note."""
    api_key = await _create_api_key(client, admin_token)

    # Create ticket
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Grammar Test",
                "description": "desc",
                "priority": "low",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    created = json.loads(create_result["result"]["content"][0]["text"])
    ticket_number = created["data"]["ticket_number"]

    # Add exactly one note
    await _mcp_call(
        client,
        "tools/call",
        {
            "name": "add_ticket_note",
            "arguments": {
                "ticket_id_or_number": ticket_number,
                "content": "Single note",
            },
        },
        api_key=api_key,
    )

    # Retrieve notes — should say "1 note"
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "get_ticket_notes",
            "arguments": {"ticket_id_or_number": ticket_number},
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["summary"] == "Found 1 note"


async def test_audit_log_includes_actor_name(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """get_ticket_audit_log includes actor_name in each entry."""
    api_key = await _create_api_key(client, admin_token)

    # Create a ticket (generates audit entries)
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Audit Actor Test",
                "description": "desc",
                "priority": "medium",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    created = json.loads(create_result["result"]["content"][0]["text"])
    ticket_id = created["data"]["id"]

    # Get audit log
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "get_ticket_audit_log",
            "arguments": {"ticket_id_or_number": ticket_id},
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    entries = tool_result["data"]["entries"]
    assert len(entries) >= 1
    # Every entry should have the actor_name key
    for entry in entries:
        assert "actor_name" in entry
    # At least one entry should have a non-null actor_name (the creator)
    actor_names = [e["actor_name"] for e in entries if e["actor_name"] is not None]
    assert len(actor_names) >= 1


async def test_tools_accept_ticket_numbers(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """update_ticket, assign_ticket, add_ticket_note, resolve_ticket, and
    get_ticket_audit_log all accept ASM-XXXX ticket numbers."""
    api_key = await _create_api_key(client, admin_token)

    # Create a ticket
    create_result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "create_ticket",
            "arguments": {
                "title": "Ticket Number Test",
                "description": "desc",
                "priority": "low",
                "assigned_group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    created = json.loads(create_result["result"]["content"][0]["text"])
    ticket_number = created["data"]["ticket_number"]

    # update_ticket by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "update_ticket",
            "arguments": {
                "ticket_id_or_number": ticket_number,
                "title": "Updated via Number",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["title"] == "Updated via Number"

    # assign_ticket by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "assign_ticket",
            "arguments": {
                "ticket_id_or_number": ticket_number,
                "group": str(test_group.id),
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"] is not None

    # add_ticket_note by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "add_ticket_note",
            "arguments": {
                "ticket_id_or_number": ticket_number,
                "content": "Note via number",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["content"] == "Note via number"

    # get_ticket_audit_log by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "get_ticket_audit_log",
            "arguments": {"ticket_id_or_number": ticket_number},
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert len(tool_result["data"]["entries"]) >= 1

    # resolve_ticket by ticket number
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "resolve_ticket",
            "arguments": {
                "ticket_id_or_number": ticket_number,
                "resolution_note": "Resolved via number",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"]["status"] == "resolved"


async def test_bulk_update_error_includes_ticket_context(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
):
    """bulk_update_tickets error message includes the ticket identifier."""
    api_key = await _create_api_key(client, admin_token)

    fake_id = "00000000-0000-0000-0000-000000000099"
    result = await _mcp_call(
        client,
        "tools/call",
        {
            "name": "bulk_update_tickets",
            "arguments": {
                "ticket_ids": [fake_id],
                "status": "resolved",
            },
        },
        api_key=api_key,
    )
    tool_result = json.loads(result["result"]["content"][0]["text"])
    assert tool_result["data"] is None
    # The error message should contain the ticket ID that failed
    assert fake_id in tool_result["summary"] or "not found" in tool_result["summary"].lower()
