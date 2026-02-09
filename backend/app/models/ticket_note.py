import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class TicketNote(TimestampMixin, Base):
    __tablename__ = "ticket_notes"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], lazy="raise")
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="notes", lazy="raise")

    @property
    def author_name(self) -> str | None:
        try:
            return self.author.full_name
        except Exception:
            return None
