from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from scout.utils.storage.postgres_models_llm import LLMModel as SqLLMModel
from scout.DataIngest.models.llm_schemas import LLMModel as PyLLMModel
from scout.DataIngest.models.llm_schemas import LLMModelCreate


def get_llm_models(db: Session) -> List[PyLLMModel]:
    """
    Get all available LLM models.
    """
    models = db.execute(select(SqLLMModel)).scalars().all()
    return [PyLLMModel.from_orm(model) for model in models]


def get_default_llm_model(db: Session) -> Optional[PyLLMModel]:
    """
    Get the default LLM model.
    """
    model = db.execute(select(SqLLMModel).where(SqLLMModel.is_default.is_(True))).scalar_one_or_none()
    if model:
        return PyLLMModel.from_orm(model)
    return None


def get_llm_model_by_id(db: Session, model_id: UUID) -> Optional[PyLLMModel]:
    """
    Get an LLM model by its ID.
    """
    model = db.execute(select(SqLLMModel).where(SqLLMModel.id == model_id)).scalar_one_or_none()
    if model:
        return PyLLMModel.from_orm(model)
    return None


def create_llm_model(db: Session, model: LLMModelCreate) -> PyLLMModel:
    """
    Create a new LLM model.
    """
    # If setting this model as default, clear other defaults
    if model.is_default:
        db.execute(select(SqLLMModel).where(SqLLMModel.is_default.is_(True)).update({SqLLMModel.is_default: False}))
    
    sq_model = SqLLMModel(**model.dict())
    db.add(sq_model)
    db.commit()
    db.refresh(sq_model)
    return PyLLMModel.from_orm(sq_model)
