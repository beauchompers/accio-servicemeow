import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TicketPriority, TicketStatus, TimestampMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.audit_log import AuditLog
    from app.models.group import Group
    from app.models.ticket_note import TicketNote
    from app.models.user import User


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_assigned_group_id", "assigned_group_id"),
        Index("ix_tickets_assigned_user_id", "assigned_user_id"),
        Index("ix_tickets_created_at", "created_at"),
    )

    ticket_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        ENUM(TicketStatus, name="ticketstatus", create_type=True),
        default=TicketStatus.open,
        server_default="open",
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        ENUM(TicketPriority, name="ticketpriority", create_type=True), nullable=False
    )
    assigned_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True
    )
    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_target_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sla_target_assign_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Relationships
    assigned_group: Mapped[Optional["Group"]] = relationship(
        "Group", foreign_keys=[assigned_group_id], lazy="raise"
    )
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_user_id], lazy="raise"
    )
    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_id], lazy="raise"
    )
    notes: Mapped[list["TicketNote"]] = relationship(
        "TicketNote", back_populates="ticket", lazy="raise"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="ticket", lazy="raise"
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="ticket", lazy="raise"
    )

    @property
    def created_by_name(self) -> str | None:
        try:
            return self.created_by.full_name
        except Exception:
            return None

    @property
    def assigned_user_name(self) -> str | None:
        try:
            return self.assigned_user.full_name if self.assigned_user else None
        except Exception:
            return None

    @property
    def assigned_group_name(self) -> str | None:
        try:
            return self.assigned_group.name if self.assigned_group else None
        except Exception:
            return None
