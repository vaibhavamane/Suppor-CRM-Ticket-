from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ticket_schema import (
    TicketCreate,
    TicketCreateResponse,
    TicketListResponse,
    TicketDetailResponse,
    TicketUpdate,
    TicketUpdateResponse
)
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post(
    "",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ticket"
)
async def create_new_ticket(
    ticket_in: TicketCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new customer support ticket.
    Generates a unique Ticket ID and registers search tokens in the Bloom Filter.
    """
    try:
        ticket = await ticket_service.create_ticket(db, ticket_in)
        return ticket
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the ticket: {str(e)}"
        )

@router.get(
    "",
    response_model=List[TicketListResponse],
    summary="List all tickets with filtering and search"
)
async def list_tickets(
    response: Response,
    status: Optional[str] = Query(None, pattern="^(Open|In Progress|Closed)$", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search query across ticket ID, name, email, subject, description"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(4, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of tickets.
    Supports filtering by status, search, and pagination.
    Integrates Bloom Filter checks to speed up negative search queries.
    """
    try:
        # Get total matching count for pagination headers
        total_count = await ticket_service.get_tickets_count(db, status, search)
        
        tickets = await ticket_service.get_tickets(
            db=db,
            status=status,
            search=search,
            page=page,
            limit=limit
        )
        
        # Set count header and expose it for CORS/client-side access
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
        
        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickets: {str(e)}"
        )

@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get single ticket details with notes"
)
async def get_ticket_details(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the complete details of a specific ticket, including all associated notes.
    """
    ticket = await ticket_service.get_ticket_by_id(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )
    return ticket

@router.put(
    "/{ticket_id}",
    response_model=TicketUpdateResponse,
    summary="Update ticket status and/or add notes"
)
async def update_existing_ticket(
    ticket_id: str,
    ticket_update: TicketUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates an existing ticket's status and adds a comment/note if provided in the body.
    """
    if ticket_update.status is None and ticket_update.notes is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field ('status' or 'notes') must be provided for update."
        )
        
    ticket = await ticket_service.update_ticket(
        db=db,
        ticket_id=ticket_id,
        status=ticket_update.status,
        new_note_text=ticket_update.notes
    )
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID {ticket_id} not found."
        )
        
    return TicketUpdateResponse(
        success=True,
        updated_at=ticket.updated_at
    )
