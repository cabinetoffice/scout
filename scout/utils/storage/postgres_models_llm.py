import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from scout.utils.storage.postgres_database import Base


class LLMModel(Base):
    __tablename__ = "llm_model"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    name = Column(String, nullable=False)
    model_id = Column(String, nullable=False, unique=True)  # The actual model ID used with Bedrock
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())
