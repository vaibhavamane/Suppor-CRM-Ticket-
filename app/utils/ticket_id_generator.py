import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import Ticket

async def generate_next_ticket_id(db: AsyncSession) -> str:
    """
    Generates the next sequential ticket ID in the format TKT-XXX.
    Reads the highest ID from the DB to determine the next counter value.
    """
    # Fetch the ticket with the highest primary key ID to find the last created ticket_id
    stmt = select(Ticket.ticket_id).order_by(Ticket.id.desc()).limit(1)
    result = await db.execute(stmt)
    last_ticket_id = result.scalar_one_or_none()

    if not last_ticket_id:
        return "TKT-001"

    # Extract the numeric suffix and increment it
    match = re.match(r"^TKT-(\d+)$", last_ticket_id)
    if match:
        current_num = int(match.group(1))
        next_num = current_num + 1
        return f"TKT-{next_num:03d}"
    
    # Fallback if the format doesn't match
    return "TKT-001"
