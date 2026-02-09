from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TicketPriority, TimestampMixin


class SlaConfig(TimestampMixin, Base):
    __tablename__ = "sla_config"

    priority: Mapped[TicketPriority] = mapped_column(
        ENUM(TicketPriority, name="ticketpriority", create_type=True),
        unique=True,
        nullable=False,
    )
    target_assign_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_resolve_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
