import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func
from sqlalchemy.exc import IntegrityError

from app.models.ticket import Ticket
from app.models.note import Note
from app.schemas.ticket_schema import TicketCreate
from app.services.bloom_service import bloom_service
from app.utils.ticket_id_generator import generate_next_ticket_id

logger = logging.getLogger("ticket_service")

async def create_ticket(db: AsyncSession, ticket_in: TicketCreate) -> Ticket:
    """
    Creates a ticket in the database.
    Generates a unique sequential ticket ID, retrying in case of database collisions.
    Inserts search tokens for the ticket into the Bloom Filter.
    """
    max_retries = 5
    ticket = None

    for attempt in range(max_retries):
        ticket_id = await generate_next_ticket_id(db)
        ticket = Ticket(
            ticket_id=ticket_id,
            customer_name=ticket_in.customer_name,
            customer_email=ticket_in.customer_email,
            subject=ticket_in.subject,
            description=ticket_in.description,
            status="Open"
        )
        
        db.add(ticket)
        try:
            await db.commit()
            await db.refresh(ticket)
            break
        except IntegrityError:
            await db.rollback()
            logger.warning(f"Ticket ID collision on {ticket_id}. Retrying creation (attempt {attempt + 1}/{max_retries})...")
            if attempt == max_retries - 1:
                raise RuntimeError("Failed to generate a unique ticket ID after maximum retries.")
    
    # Update Bloom Filter cache
    bloom_service.add_ticket(ticket)
    logger.info(f"Created ticket {ticket.ticket_id} and added to Bloom Filter.")
    return ticket

async def get_tickets(
    db: AsyncSession,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> List[Ticket]:
    """
    Lists tickets with status filtering, keyword search, and pagination.
    Uses the Bloom Filter cache to bypass the database when the search query is definitely not found.
    """
    # 1. Bloom Filter Search Optimization
    if search and search.strip():
        # Check if query tokens exist in Bloom Filter
        might_exist = bloom_service.check_query(search)
        if not might_exist:
            # The search query definitely does not exist. Bypassing database call entirely.
            logger.info(f"Bypassing database query for search query: '{search}'")
            return []

    # 2. Query construction
    stmt = select(Ticket)
    
    conditions = []
    
    if status:
        conditions.append(Ticket.status == status)
        
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Ticket.ticket_id.ilike(search_term),
                Ticket.customer_name.ilike(search_term),
                Ticket.customer_email.ilike(search_term),
                Ticket.subject.ilike(search_term),
                Ticket.description.ilike(search_term)
            )
        )
        
    if conditions:
        stmt = stmt.where(and_(*conditions))
        
    # Order by creation date (newest first)
    stmt = stmt.order_by(Ticket.created_at.desc())
    
    # Pagination
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(stmt)
    tickets = result.scalars().all()
    return list(tickets)

async def get_tickets_count(
    db: AsyncSession,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> int:
    """
    Returns the total count of tickets matching status and search query.
    Used for pagination metadata.
    """
    if search and search.strip():
        might_exist = bloom_service.check_query(search)
        if not might_exist:
            return 0

    stmt = select(func.count(Ticket.id))
    
    conditions = []
    if status:
        conditions.append(Ticket.status == status)
        
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        conditions.append(
            or_(
                Ticket.ticket_id.ilike(search_term),
                Ticket.customer_name.ilike(search_term),
                Ticket.customer_email.ilike(search_term),
                Ticket.subject.ilike(search_term),
                Ticket.description.ilike(search_term)
            )
        )
        
    if conditions:
        stmt = stmt.where(and_(*conditions))
        
    result = await db.execute(stmt)
    return result.scalar() or 0

async def get_ticket_by_id(db: AsyncSession, ticket_id: str) -> Optional[Ticket]:
    """
    Retrieves a single ticket by its ticket_id, along with its notes.
    """
    stmt = select(Ticket).where(Ticket.ticket_id == ticket_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def update_ticket(
    db: AsyncSession,
    ticket_id: str,
    status: Optional[str] = None,
    new_note_text: Optional[str] = None
) -> Optional[Ticket]:
    """
    Updates the ticket's status and adds a note if provided.
    """
    ticket = await get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
        
    if status:
        ticket.status = status
        
    if new_note_text:
        note = Note(
            ticket_id=ticket_id,
            note_text=new_note_text
        )
        db.add(note)
        
    await db.commit()
    await db.refresh(ticket)
    
    # Add new note/status text tokens to Bloom filter to allow searching updated comments
    if new_note_text:
        # Since pybloom-live doesn't support deleting or modifying entries easily,
        # we simply add the new tokens to the Bloom Filter.
        # This keeps the search index updated.
        tokens = bloom_service.get_searchable_tokens(
            ticket_id=ticket.ticket_id,
            customer_name=ticket.customer_name,
            customer_email=ticket.customer_email,
            subject=ticket.subject,
            description=ticket.description + " " + new_note_text
        )
        for token in tokens:
            bloom_service.bf.add(token)
            
    logger.info(f"Updated ticket {ticket_id} (Status: {ticket.status}, Added Note: {bool(new_note_text)}).")
    return ticket
