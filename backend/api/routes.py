import base64
from datetime import datetime
import json
import logging
import typing
from functools import lru_cache
from typing import Annotated, List
from typing import Optional
from uuid import UUID
from sqlalchemy import select

import requests
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import Response
from pydantic import BaseModel

from backend.utils.filters import Filters
from backend.utils.rating_request import RatingRequest
from scout.DataIngest.models.schemas import Chunk as PyChunk
from scout.DataIngest.models.schemas import ChunkFilter
from scout.DataIngest.models.schemas import Criterion as PyCriterion
from scout.DataIngest.models.schemas import CriterionFilter
from scout.DataIngest.models.schemas import File as PyFile
from scout.DataIngest.models.schemas import FileFilter
from scout.DataIngest.models.schemas import Project as PyProject
from scout.DataIngest.models.schemas import ProjectFilter
from scout.DataIngest.models.schemas import Rating as PyRating
from scout.DataIngest.models.schemas import RatingCreate
from scout.DataIngest.models.schemas import RatingFilter
from scout.DataIngest.models.schemas import RatingUpdate
from scout.DataIngest.models.schemas import Result as PyResult
from scout.DataIngest.models.schemas import ResultFilter
from scout.DataIngest.models.schemas import User as PyUser
from scout.DataIngest.models.schemas import UserCreate
from scout.DataIngest.models.schemas import UserFilter
from scout.DataIngest.models.schemas import UserUpdate
from scout.utils.config import Settings
from scout.utils.storage.postgres_models import project_users
from scout.utils.storage import postgres_interface as interface
from scout.utils.storage.postgres_database import SessionLocal
import os
import boto3
from botocore.exceptions import ClientError


router = APIRouter()


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()

SECRET_KEY = settings.API_JWT_KEY
ALGORITHM = "HS256"


models = {
    "result": PyResult,
    "criterion": PyCriterion,
    "chunk": PyChunk,
    "file": PyFile,
    "project": PyProject,
    "user": PyUser,
    "rating": PyRating,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TokenData(BaseModel):
    username: str


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__) 
    
def extract_oidc_from_token(token: str) -> Optional[str]:
    """Extract x_amzn_oidc_data from the JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)  # Fix base64 padding
        decoded = base64.urlsafe_b64decode(payload).decode("utf-8")
        token_content = json.loads(decoded)
        return json.dumps(token_content)  # Return raw OIDC data
    except Exception as e:
        logger.error(f"Failed to decode token: {e}")
        return None

def get_current_user(
    request: Request,
    x_amzn_oidc_data: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> Optional[PyUser]:
    
    logger.info(f"ENVIRONMENT: {settings.ENVIRONMENT}")
    
    if settings.ENVIRONMENT == "local":
        # A JWT for local testing
        authorization = f"Bearer {settings.API_JWT_KEY}"

    """Extract user information from the OIDC token."""
    logger.info(f"Incoming Headers: {dict(request.headers)}")
    logger.info(f"x-amzn-oidc-data Header: {x_amzn_oidc_data}")
    logger.info(f"Authorization Header: {authorization}")

    if not x_amzn_oidc_data and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        x_amzn_oidc_data = extract_oidc_from_token(token)
        logger.info(f"Extracted x-amzn-oidc-data from token: {x_amzn_oidc_data}")
    
    if not x_amzn_oidc_data:
        raise HTTPException(status_code=401, detail="OIDC data not found in headers or token")
    
    try:
        token_data = json.loads(x_amzn_oidc_data)
        email = token_data.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Email not found in token")
        
        users = interface.filter_items(UserFilter(email=email), None)
        user = users[0] if users else None

        if user:
            
            user_projects_ids = [row.project_id for row in SessionLocal().execute(select(project_users).where(project_users.c.user_id == user.id)).all()]
            projects = [interface.get_by_id(PyProject, project_id) for project_id in user_projects_ids]
            user.projects = projects
            logger.info(f"user projects: {user.projects}")
            updated_user = interface.update_item(
                UserUpdate(id=user.id, email=user.email, updated_datetime=datetime.utcnow(), role=user.role)
            )
            return updated_user

        return interface.get_or_create_item(UserCreate(email=email, projects=projects))
        
    except Exception as e:
        logger.error(f"Error processing user: {e}")
        raise HTTPException(status_code=401, detail="Failed to process OIDC data")

def is_item_in_user_projects(
    item: PyUser | PyRating | PyFile | PyProject | PyResult | PyCriterion | PyChunk,
    user: PyUser,
) -> bool:
    user_projects_ids = [row.project_id for row in SessionLocal().execute(select(project_users).where(project_users.c.user_id == user.id)).all()]
    user_projects = [interface.get_by_id(PyProject, project_id) for project_id in user_projects_ids]
    user_project_names = [project.name for project in user_projects]

    
    
    if type(item) is PyProject:
        item = typing.cast(PyProject, item)
        if item.name in user_project_names:
            return True
    if type(item) is PyUser:
        return True
    if type(item) is PyRating:
        item = typing.cast(PyRating, item)
        if item.project.name in user_project_names:
            return True
    if type(item) is PyFile:
        item = typing.cast(PyFile, item)
        if item.project.name in user_project_names:
            return True
    if type(item) is PyResult:
        item = typing.cast(PyResult, item)
        if item.project.name in user_project_names:
            return True
    if type(item) is PyCriterion:
        item = typing.cast(PyCriterion, item)
        criterion_project_names = [project.name for project in item.projects]
        if any(project_name in user_project_names for project_name in criterion_project_names):
            return True
    if type(item) is PyChunk:
        item = typing.cast(PyChunk, item)
        file = interface.get_by_id(PyFile, item.file.id)
        if file.project.name in user_project_names:
            return True
    logger.info(f"Item {item.id} not available to user {user.id}")
    return False


@router.get("/item/{table}")
def get_items(
    request: Request,
    table: str,
    uuid: Optional[UUID] = Query(None),
    current_user: PyUser = Depends(get_current_user),
):
    logger.log(level=logging.INFO, msg=request)
    model = models.get(table.lower())
    if not model:
        raise HTTPException(status_code=400, detail="Invalid table name")

    if uuid:
        item = interface.get_by_id(model, uuid)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
    else:
        items = interface.get_all(model)
        return [item for item in items if is_item_in_user_projects(item, current_user)]


@router.get("/related/{uuid}/{model1}/{model2}")
def get_related_items(
    uuid: UUID | None,
    model1: str,
    model2: str,
    limit_to_user: Optional[bool] = False,
    current_user: PyUser = Depends(get_current_user),
):
    source_model = models.get(model1.lower())
    target_model = models.get(model2.lower())
    if not source_model or not target_model:
        raise HTTPException(status_code=400, detail="Invalid model names")

    source_item = interface.get_by_id(source_model, uuid)
    target_items = source_item.dict().get(f"{model2.lower()}s", [])
    populated_target_items = [interface.get_by_id(target_model, item["id"]) for item in target_items]
    if limit_to_user:
        populated_target_items = [
            populated_target_item
            for populated_target_item in populated_target_items
            if populated_target_item.user.id == current_user.id
        ]
    return populated_target_items


@router.post("/read_items_by_attribute")
def read_items_by_attribute(
    filters: Filters,
    request: Request,
    current_user: PyUser = Depends(get_current_user),
):
    logger.info(f"headers: {request.headers}")
    model = models.get(filters.model.lower())
    if not model:
        raise HTTPException(status_code=400, detail="Invalid model name")

    items = []
    if model is PyProject:
        filter = ProjectFilter(
            name=filters.filters.get("name", None),
            results_summary=filters.filters.get("results_summary", None),
        )
        items = interface.filter_items(filter, current_user)
    if model is PyFile:
        filter = FileFilter(
            name=filters.filters.get("name", None),
            type=filters.filters.get("type", None),
            clean_name=filters.filters.get("clean_name", None),
            summary=filters.filters.get("summary", None),
            source=filters.filters.get("source", None),
        )
        items = interface.filter_items(filter, current_user)
    if model is PyResult:
        filter = ResultFilter(
            answer=filters.filters.get("answer", None),
            full_text=filters.filters.get("full_text", None),
        )
        items = interface.filter_items(filter, current_user)
    if model is PyCriterion:
        filter = CriterionFilter(
            gate=filters.filters.get("gate", None),
            category=filters.filters.get("category", None),
            question=filters.filters.get("question", None),
            evidence=filters.filters.get("evidence", None),
        )
        items = interface.filter_items(filter, current_user)
    if model is PyChunk:
        filter = ChunkFilter(
            idx=filters.filters.get("idx", None),
            text=filters.filters.get("text", None),
            page_num=filters.filters.get("page_num", None),
        )
        items = interface.filter_items(filter, current_user)
    if model is PyUser:
        filter = UserFilter(
            username=filters.filters.get("username", None),
            name=filters.filters.get("name", None),
        )
        items = interface.filter_items(filter)
    return items


@router.get("/get_file/{uuid}")
def get_file(
    uuid: UUID,
    current_user: PyUser = Depends(get_current_user),
):
    try:
        file = interface.get_by_id(PyFile, uuid)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        file_extension = file.s3_key.split(".")[-1].lower()

        if file_extension == "pdf":
            file_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
        # Replace this file.url with a pre-signed url from a s3 bucket to test with remote files
        file_response = requests.get(file.url)
        file_response.raise_for_status()
        file_content = file_response.content
        return Response(
            content=file_content,
            media_type=file_type,
            headers={
                "Content-Disposition": f"attachment; filename={file.s3_key.split('/')[-1]}",
                "X-File-Type": file_type,
            },
        )

    except Exception as e:
        logger.exception("An error occurred while retrieving the file")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving the file: {str(e)}",
        )


@router.post("/rate")
def rate_response(
    rating_request: RatingRequest,
    current_user: PyUser = Depends(get_current_user),
):
    result = interface.get_by_id(PyResult, rating_request.result_id)
    if not result:
        return Response("Referenced result not found", 404)
    existing_rating = interface.filter_items(RatingFilter(user=current_user, result=result, project=result.project))
    if existing_rating:
        updated_item = interface.update_item(
            RatingUpdate(
                id=existing_rating[0].id,
                user=current_user,
                result=result,
                project=result.project,
                positive_rating=rating_request.good_response,
            )
        )
        return {"message": f"Rating {updated_item.id} submitted successfully"}
    else:
        new_rating = RatingCreate(
            user=current_user,
            result=result,
            project=result.project,
            positive_rating=rating_request.good_response,
        )
        response = interface.get_or_create_item(new_rating)
        return {"message": f"Rating {response.id} submitted successfully"}


@router.post("/add_user_to_project/{user_id}/{project_id}")
def add_user_to_project(
    user_id: UUID,
    project_id: UUID,
    current_user: PyUser = Depends(get_current_user),
):
    """Adds a user to a project."""
    user = interface.get_by_id(PyUser, user_id)
    project = interface.get_by_id(PyProject, project_id)

    if not user or not project:
        raise HTTPException(status_code=404, detail="User or project not found")

    with interface.SessionManager() as db:
        db.execute(
            project_users.insert().values(user_id=user.id, project_id=project.id)
        )
        db.commit()

    return {"message": f"User {user.id} added to project {project.id}"}


@router.delete("/remove_user_from_project/{user_id}/{project_id}")
def remove_user_from_project(
    user_id: UUID,
    project_id: UUID,
    current_user: PyUser = Depends(get_current_user),
):
    """Removes a user from a project."""
    user = interface.get_by_id(PyUser, user_id)
    project = interface.get_by_id(PyProject, project_id)

    if not user or not project:
        raise HTTPException(status_code=404, detail="User or project not found")

    with interface.SessionManager() as db:
        db.execute(project_users.delete().where((project_users.c.user_id == user.id) & (project_users.c.project_id == project.id)))
        db.commit()
    return {"message": f"User {user.id} removed from project {project.id}"}

  
@router.get("/admin/users")
def get_all_users_with_projects(
    request: Request,
    current_user: PyUser = Depends(get_current_user),
):
    logger.log(level=logging.INFO, msg=request)
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        users = interface.filter_items(UserFilter(), current_user)

        return users
    except Exception as e:
        logger.error(f"Error fetching all users: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching all users: {e}")


@router.post("/custom-query")
def custom_query(
    query: str,
    current_user: PyUser = Depends(get_current_user),
):
    model_id = os.getenv("AWS_BEDROCK_MODEL_ID")
    knowledge_id = os.getenv("AWS_BEDROCK_KB_ID")

    if not model_id or not knowledge_id:
        raise HTTPException(status_code=500, detail="Model ID or Knowledge ID not found in environment variables")

    client = boto3.client('lambda')

    payload = {
        "query": str(query),
        "modelId": str(model_id),
        "knowledgeBaseId": str(knowledge_id)
    }

    try:
        response = client.invoke(
            FunctionName='bd_base_query145',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        response_payload = json.loads(response['Payload'].read())
        return response_payload
    except ClientError as e:
        logger.error(f"An error occurred while invoking the Lambda function: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while invoking the Lambda function")
