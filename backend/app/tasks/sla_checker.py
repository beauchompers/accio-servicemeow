import asyncio
import logging

from sqlalchemy import select

from app.database import async_session
from app.models.ticket import Ticket
from app.models.base import TicketStatus
from app.services import sla_service

logger = logging.getLogger(__name__)

_breached_ticket_ids: set[str] = set()


async def check_sla_breaches():
    """Runs every 60 seconds, checks open tickets for SLA breaches and logs warnings."""
    while True:
        try:
            async with async_session() as db:
                # Query open/under_investigation tickets with SLA targets
                result = await db.execute(
                    select(Ticket).where(
                        Ticket.status.in_([TicketStatus.open, TicketStatus.under_investigation]),
                        Ticket.sla_target_minutes.isnot(None),
                    )
                )
                tickets = result.scalars().all()
                breached_count = 0
                for ticket in tickets:
                    if sla_service.is_breached(ticket):
                        breached_count += 1
                        logger.warning(
                            "SLA breached for ticket %s (elapsed: %ds, target: %ds)",
                            ticket.ticket_number,
                            sla_service.calculate_elapsed_seconds(ticket),
                            ticket.sla_target_minutes * 60,
                        )
                        _breached_ticket_ids.add(str(ticket.id))
                if breached_count > 0:
                    logger.info("SLA check complete: %d breached tickets", breached_count)
        except Exception:
            logger.exception("SLA check failed")
        await asyncio.sleep(60)
