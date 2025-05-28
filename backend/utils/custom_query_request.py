from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class CustomQueryRequest(BaseModel):
    query: str
    chat_session_id: Optional[UUID] = None
    model_id: Optional[str] = None
    prompt_template: Optional[str] = None