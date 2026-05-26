from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.note_schema import NoteResponse

class TicketCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=100)
    customer_email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)

class TicketCreateResponse(BaseModel):
    ticket_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TicketListResponse(BaseModel):
    ticket_id: str
    customer_name: str
    subject: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TicketDetailResponse(BaseModel):
    ticket_id: str
    customer_name: str
    customer_email: str
    subject: str
    description: str
    status: str
    notes: List[NoteResponse]

    model_config = ConfigDict(from_attributes=True)

class TicketUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(Open|In Progress|Closed)$")
    notes: Optional[str] = Field(None, min_length=1)

class TicketUpdateResponse(BaseModel):
    success: bool
    updated_at: datetime
