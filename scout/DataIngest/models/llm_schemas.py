from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class LLMModelBase(BaseModel):
    name: str
    model_id: str
    description: Optional[str] = None
    is_default: bool = False


class LLMModelCreate(LLMModelBase):
    pass


class LLMModel(LLMModelBase):
    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime] = None

    class Config:
        from_attributes = True


class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    model_id: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
