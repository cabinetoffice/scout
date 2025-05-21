from fastapi import APIRouter, Depends
from typing import List

from backend.api.routes import get_current_user, get_db
from scout.DataIngest.models.schemas import User as PyUser
from scout.DataIngest.models.llm_schemas import LLMModel
from scout.utils.storage.postgres_interface_llm import get_llm_models, get_default_llm_model

router = APIRouter()

@router.get("/models", response_model=List[LLMModel])
def list_available_models(
    current_user: PyUser = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get all available LLM models."""
    return get_llm_models(db)

@router.get("/models/default", response_model=LLMModel)
def get_default_model(
    current_user: PyUser = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get the default LLM model."""
    model = get_default_llm_model(db)
    return model
