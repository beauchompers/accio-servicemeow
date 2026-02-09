import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import ActorType, Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class AuditLog(Base):
    """Audit log entries are immutable — no updated_at column."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_ticket_id", "ticket_id"),
        Index("ix_audit_log_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_type: Mapped[ActorType] = mapped_column(
        ENUM(ActorType, name="actortype", create_type=True), nullable=False
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    field_changed: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="audit_entries")
    actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_id])

    @property
    def actor_name(self) -> str | None:
        try:
            return self.actor.full_name if self.actor else None
        except Exception:
            return None
