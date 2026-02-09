import pytest
from httpx import AsyncClient

from app.models.group import Group, GroupMembership
from app.models.sla_config import SlaConfig
from app.models.user import User
from tests.conftest import auth_header


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ticket_payload(group_id: str, **overrides) -> dict:
    """Build a minimal valid ticket creation payload."""
    base = {
        "title": "Test ticket",
        "description": "desc",
        "priority": "medium",
        "assigned_group_id": group_id,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Ticket CRUD
# ---------------------------------------------------------------------------


async def test_create_ticket(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """POST /api/v1/tickets/ creates a ticket and returns 201 with a ticket number."""
    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Test ticket", description="Test description"),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    data = response.json()
    assert data["ticket_number"].startswith("ASM-")
    assert data["title"] == "Test ticket"
    assert data["status"] == "open"
    assert data["priority"] == "medium"


async def test_list_tickets_pagination(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """Create multiple tickets and verify pagination works."""
    for i in range(3):
        await client.post(
            "/api/v1/tickets/",
            json=_ticket_payload(str(test_group.id), title=f"Ticket {i}", priority="low"),
            headers=auth_header(admin_token),
        )

    response = await client.get(
        "/api/v1/tickets/?page=1&page_size=2",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["pages"] == 2


async def test_get_ticket_detail(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/{id} returns detail with notes, attachments, and audit_log."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Detail test", priority="high"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["title"] == "Detail test"
    assert "notes" in data
    assert "attachments" in data
    assert "audit_log" in data


async def test_update_ticket_status(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """PATCH /api/v1/tickets/{id} transitions status to under_investigation."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Status test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "under_investigation"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "under_investigation"


async def test_resolve_ticket_sets_resolved_at(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """Resolving a ticket populates the resolved_at timestamp."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Resolve test", priority="low"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["resolved_at"] is not None


async def test_soft_delete_ticket(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """DELETE /api/v1/tickets/{id} soft-deletes the ticket and returns 204."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Delete test", priority="low"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.delete(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


async def test_add_note_to_ticket(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """POST /api/v1/tickets/{id}/notes creates a note and returns 201."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Note test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        json={"content": "This is a note", "is_internal": False},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    assert response.json()["content"] == "This is a note"
    assert response.json()["is_internal"] is False


async def test_list_notes(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/{id}/notes returns all notes for the ticket."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="List notes test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        json={"content": "Note 1", "is_internal": False},
        headers=auth_header(admin_token),
    )
    await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        json={"content": "Note 2", "is_internal": True},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/notes",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    notes = response.json()
    assert len(notes) >= 2


async def test_edit_note(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """PATCH /api/v1/tickets/{id}/notes/{note_id} updates the note content."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Edit note test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    note_response = await client.post(
        f"/api/v1/tickets/{ticket_id}/notes",
        json={"content": "Original", "is_internal": False},
        headers=auth_header(admin_token),
    )
    note_id = note_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/notes/{note_id}",
        json={"content": "Updated content"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------


async def test_upload_attachment(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """POST /api/v1/tickets/{id}/attachments uploads a file and returns 201."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Attachment test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("test.txt", b"hello world", "text/plain")},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201

    data = response.json()
    assert data["original_filename"] == "test.txt"
    assert data["content_type"] == "text/plain"
    assert data["ticket_id"] == ticket_id


async def test_list_attachments(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/{id}/attachments lists uploaded attachments."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="List attachments test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    await client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/attachments",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    attachments = response.json()
    assert len(attachments) >= 1
    assert attachments[0]["original_filename"] == "doc.pdf"


# ---------------------------------------------------------------------------
# SLA
# ---------------------------------------------------------------------------


async def test_ticket_detail_includes_sla_status(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/{id} includes sla_status in detail response."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="SLA test", priority="critical"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    # sla_status may be None if no SLA target is set, or a dict with SLA fields
    if data["sla_target_minutes"] is not None:
        assert "sla_status" in data
        sla = data["sla_status"]
        assert "elapsed_minutes" in sla
        assert "target_minutes" in sla
        assert "is_breached" in sla
        assert "is_at_risk" in sla
        assert "remaining_minutes" in sla
        assert "percentage" in sla


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


async def test_audit_log_shows_creation(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """Creating a ticket produces an audit log entry with action 'created'."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Audit test", priority="high"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/audit-log",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    entries = response.json()
    assert len(entries) >= 1
    assert any(e["action"] == "created" for e in entries)


async def test_audit_log_shows_update(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """Updating a ticket status creates an audit log entry for the changed field."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Audit update test"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "under_investigation"},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/audit-log",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    entries = response.json()
    assert any(
        e["action"] == "updated" and e["field_changed"] == "status"
        for e in entries
    )


async def test_audit_log_captures_priority_change(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """Changing a ticket's priority creates an audit log entry for priority."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Priority audit test", priority="low"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"priority": "critical"},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/audit-log",
        headers=auth_header(admin_token),
    )
    entries = response.json()
    assert any(
        e["action"] == "updated" and e["field_changed"] == "priority"
        for e in entries
    )


# ---------------------------------------------------------------------------
# Unauthenticated requests
# ---------------------------------------------------------------------------


async def test_create_ticket_unauthenticated(client: AsyncClient):
    """POST /api/v1/tickets/ without auth returns 401."""
    response = await client.post(
        "/api/v1/tickets/",
        json={"title": "No auth", "description": "desc", "priority": "low", "assigned_group_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 401


async def test_list_tickets_unauthenticated(client: AsyncClient):
    """GET /api/v1/tickets/ without auth returns 401."""
    response = await client.get("/api/v1/tickets/")
    assert response.status_code == 401


async def test_get_ticket_unauthenticated(client: AsyncClient):
    """GET /api/v1/tickets/{id} without auth returns 401."""
    response = await client.get("/api/v1/tickets/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_get_nonexistent_ticket(client: AsyncClient, admin_token: str):
    """GET /api/v1/tickets/{id} for a non-existent ID returns 404."""
    response = await client.get(
        "/api/v1/tickets/00000000-0000-0000-0000-000000000099",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


async def test_update_ticket_priority(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """PATCH /api/v1/tickets/{id} can change the ticket priority."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Priority change", priority="low"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"priority": "high"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["priority"] == "high"


async def test_update_ticket_title(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """PATCH /api/v1/tickets/{id} can update the ticket title."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Original title"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"title": "Updated title"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"


async def test_filter_tickets_by_status(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/?status=open filters by status."""
    for i in range(2):
        await client.post(
            "/api/v1/tickets/",
            json=_ticket_payload(str(test_group.id), title=f"Filter ticket {i}"),
            headers=auth_header(admin_token),
        )

    response = await client.get(
        "/api/v1/tickets/?status=open",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert all(item["status"] == "open" for item in data["items"])


async def test_filter_tickets_by_priority(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """GET /api/v1/tickets/?priority=critical filters by priority."""
    await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Critical ticket", description="urgent", priority="critical"),
        headers=auth_header(admin_token),
    )
    await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Low ticket", description="not urgent", priority="low"),
        headers=auth_header(admin_token),
    )

    response = await client.get(
        "/api/v1/tickets/?priority=critical",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert all(item["priority"] == "critical" for item in data["items"])


# ---------------------------------------------------------------------------
# Group assignment validation
# ---------------------------------------------------------------------------


async def test_create_ticket_without_group_returns_422(
    client: AsyncClient, admin_token: str,
):
    """POST /api/v1/tickets/ without assigned_group_id returns 422."""
    response = await client.post(
        "/api/v1/tickets/",
        json={"title": "No group", "description": "desc", "priority": "medium"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 422


async def test_create_ticket_nonexistent_group_returns_404(
    client: AsyncClient, admin_token: str,
):
    """POST /api/v1/tickets/ with nonexistent group returns 404."""
    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload("00000000-0000-0000-0000-000000000099", title="Bad group"),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 404


async def test_create_ticket_user_not_in_group_returns_422(
    client: AsyncClient, admin_token: str, admin_user: User, test_group: Group,
):
    """POST /api/v1/tickets/ with user not in the assigned group returns 422."""
    # admin_user exists but is NOT in test_group (admin_in_group fixture not requested)
    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(
            str(test_group.id),
            title="User not in group",
            assigned_user_id=str(admin_user.id),
        ),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 422


async def test_create_ticket_user_in_group_returns_201(
    client: AsyncClient, admin_token: str, admin_user: User, test_group: Group, admin_in_group: GroupMembership,
):
    """POST /api/v1/tickets/ with user in the assigned group returns 201."""
    response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(
            str(test_group.id),
            title="User in group",
            assigned_user_id=str(admin_user.id),
        ),
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assigned_user_id"] == str(admin_user.id)
    assert data["assigned_group_id"] == str(test_group.id)


async def test_update_ticket_null_group_returns_422(
    client: AsyncClient, admin_token: str, test_group: Group, admin_in_group: GroupMembership,
):
    """PATCH /api/v1/tickets/{id} with assigned_group_id=null returns 422."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Null group update"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"assigned_group_id": None},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# MTTA + SLA Outcome
# ---------------------------------------------------------------------------


async def test_ticket_detail_includes_mtta_status(
    client: AsyncClient,
    admin_token: str,
    admin_user: User,
    test_group: Group,
    admin_in_group: GroupMembership,
    sla_config: list[SlaConfig],
):
    """GET /api/v1/tickets/{id} includes mtta_status when SLA config exists."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(
            str(test_group.id),
            title="MTTA test",
            priority="critical",
            assigned_user_id=str(admin_user.id),
        ),
        headers=auth_header(admin_token),
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["sla_target_assign_minutes"] == 15
    assert data["sla_target_minutes"] == 120
    assert data["mtta_status"] is not None
    mtta = data["mtta_status"]
    assert mtta["target_minutes"] == 15
    assert "elapsed_minutes" in mtta
    assert "percentage" in mtta
    assert "is_breached" in mtta
    assert "is_met" in mtta
    assert "is_pending" in mtta
    # Ticket was created with assignment, so first_assigned_at is set → is_met, not pending
    assert mtta["is_met"] is True
    assert mtta["is_pending"] is False


async def test_resolved_ticket_shows_sla_outcome(
    client: AsyncClient,
    admin_token: str,
    test_group: Group,
    admin_in_group: GroupMembership,
    sla_config: list[SlaConfig],
):
    """Resolved ticket detail shows outcome in sla_status."""
    create_response = await client.post(
        "/api/v1/tickets/",
        json=_ticket_payload(str(test_group.id), title="Outcome test", priority="low"),
        headers=auth_header(admin_token),
    )
    ticket_id = create_response.json()["id"]

    # Resolve immediately — should be within SLA for low priority (1440 min target)
    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"status": "resolved"},
        headers=auth_header(admin_token),
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200

    data = response.json()
    sla = data["sla_status"]
    assert sla is not None
    assert sla["is_resolved"] is True
    assert sla["outcome"] == "within_sla"
