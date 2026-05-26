from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NoteResponse(BaseModel):
    note_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
