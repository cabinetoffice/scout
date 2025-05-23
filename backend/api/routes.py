import base64
from datetime import datetime, timedelta
import json
import logging
import typing
import uuid
from functools import lru_cache
from typing import Annotated, List, Any
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, func
from sqlalchemy.orm import joinedload

import requests
from fastapi import APIRouter, UploadFile, File
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.utils.associate_user_project_request import AssociateUserToProjectRequest
from backend.utils.associate_user_role_request import AssociateUserToRoleRequest
from backend.utils.custom_query_request import CustomQueryRequest
from backend.utils.filters import Filters
from backend.utils.rating_request import RatingRequest
from scout.DataIngest.models.schemas import (
    Chunk as PyChunk,
    ChunkFilter,
    Criterion as PyCriterion,
    CriterionFilter,
    File as PyFile,
    FileFilter,
    Project as PyProject,
    ProjectFilter,
    Rating as PyRating,
    RatingCreate,
    RatingFilter,
    RatingUpdate,
    Result as PyResult,
    ResultFilter,
    User as PyUser,
    UserCreate,
    UserFilter,
    UserUpdate,
    AuditLog as PyAuditLog,
    RoleEnum,
    RoleFilter,
    Role as PyRole,
    # Add these new imports for chat sessions
    ChatSession as PyChatSession,
    ChatSessionCreate,
    ChatSessionUpdate,
)
# Also import the SQLAlchemy ChatSession model
from scout.utils.storage.postgres_models import ChatSession
from scout.utils.config import Settings
from scout.utils.storage.postgres_models import project_users
from scout.utils.storage.postgres_models import File as FileTable
from scout.utils.storage import postgres_interface as interface
from scout.utils.storage.postgres_database import SessionLocal
import os
import boto3
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

import asyncio
from backend.utils.audit import log_llm_query, log_file_operation

from scout.DataIngest.models.schemas import FileCreate
from scout.utils.storage.postgres_models import Criterion as SqCriterion
from scout.utils.storage.postgres_models import Project as SqProject
from scout.utils.storage.postgres_models import Result as SqResult
from scout.utils.storage.postgres_models import Project as SqProject
from scout.utils.storage.postgres_models import AuditLog
from scout.utils.storage.postgres_models import File as SqFile
from scout.utils.storage.postgres_models import Chunk as SqChunk
from scout.utils.storage.postgres_models import result_chunks
from scout.utils.llm_formats import format_llm_request

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
    "audit_log": PyAuditLog,
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
    # logger.info(f"Incoming Headers: {dict(request.headers)}")
    # logger.info(f"x-amzn-oidc-data Header: {x_amzn_oidc_data}")
    # logger.info(f"Authorization Header: {authorization}")

    if not x_amzn_oidc_data and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        x_amzn_oidc_data = extract_oidc_from_token(token)
        # logger.info(f"Extracted x-amzn-oidc-data from token: {x_amzn_oidc_data}")
    
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
            # logger.info(f"user projects: {user.projects}")

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

def get_s3_bucket_for_user_project(user: PyUser) -> str:
    try:
        project_id = user.projects[0].id
        # Query the database for the first file associated with the project
        row = SessionLocal().execute(
            select(FileTable).where(FileTable.project_id == project_id)
        ).first()

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No file found for the project: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="S3 bucket not found for the project")

    return row[0].s3_bucket  # unpack the first column (s3_bucket)

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
    # logger.info(f"headers: {request.headers}")
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
            criterion=filters.filters.get("criterion_id", None),  # Use UUID
            project=filters.filters.get("project_id", None)      # Use UUID
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

@router.get("/get_file_by_key/{key}")
def get_file_by_key(
    key: str,
    current_user: PyUser = Depends(get_current_user),
):
    try:
        # Find the file in the database by its S3 key
        file = interface.filter_items(FileFilter(s3_key=key), current_user)
        if not file or len(file) == 0:
            raise HTTPException(status_code=404, detail="File not found")

        file = file[0]  # Get the first matching file
        file_extension = file.s3_key.split(".")[-1].lower()

        # Determine the file type
        if file_extension == "pdf":
            file_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        # Fetch the file content from the S3 URL
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
        logger.exception("An error occurred while retrieving the file by key")
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
    existing_rating = interface.filter_items(RatingFilter(user=current_user, result=result, project=result.project), current_user)
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


@router.post("/add_user_to_project")
def add_user_to_project(
    associateUserToProjectRequest: AssociateUserToProjectRequest,
    current_user: PyUser = Depends(get_current_user),
):
    """Adds a user to a project."""
    user = interface.get_by_id(PyUser, associateUserToProjectRequest.user_id)
    project = interface.get_by_id(PyProject, associateUserToProjectRequest.project_id)

    if not user or not project:
        raise HTTPException(status_code=404, detail="User or project not found")

    with interface.SessionManager() as db:
        db.execute(
            project_users.insert().values(user_id=user.id, project_id=project.id)
        )
        db.commit()

    return {"message": f"User {user.id} added to project {project.id}"}


@router.post("/remove_user_from_project")
def remove_user_from_project(
    associateUserToProjectRequest: AssociateUserToProjectRequest,
    current_user: PyUser = Depends(get_current_user),
):
    """Removes a user from a project."""
    user = interface.get_by_id(PyUser, associateUserToProjectRequest.user_id)
    project = interface.get_by_id(PyProject, associateUserToProjectRequest.project_id)

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
    
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        users = interface.filter_items(UserFilter(), current_user)

        return users
    except Exception as e:
        logger.error(f"Error fetching all users: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching all users: {e}")

@router.get("/admin/projects")
def get_all_projects(
    request: Request,
    current_user: PyUser = Depends(get_current_user),
):
    logger.log(level=logging.INFO, msg=request)
    
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        projects = interface.filter_items(ProjectFilter(), current_user)

        return projects
    except Exception as e:
        logger.error(f"Error fetching all projects: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching all projects: {e}")

@router.post("/custom-query")
async def custom_query(
    request_data: CustomQueryRequest,
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db),
    request: Request = None
):
    """
    Handle custom query with optional chat_session_id and model_id.
    
    This endpoint will:
    1. Accept an optional chat_session_id from the frontend
    2. Pass the chat_session_id to the Lambda function
    3. Get a new or existing chat_session_id from the Lambda response
    4. Return the chat_session_id to the frontend for session management
    """
    if request_data.chat_session_id:
        print(f"Processing query for chat session: {request_data.chat_session_id}")

    model_id = request_data.model_id or os.getenv("AWS_BEDROCK_MODEL_ID")

    user_projects = current_user.projects
    if not user_projects:
        raise HTTPException(status_code=404, detail="No projects found for the current user.")
    
    knowledge_id = user_projects[0].knowledgebase_id
    
    if not model_id or not knowledge_id:
        raise HTTPException(status_code=500, detail="Model ID or Knowledge ID not found in environment variables or project table")

    client = boto3.client('lambda')

    formatted_request = format_llm_request(
        model_id=model_id,
        prompt=request_data.query,
        max_tokens=1000
    )

    payload = {
        "query": str(formatted_request),
        "modelId": str(model_id),
        "knowledgeBaseId": str(knowledge_id)
    }
    
    # Add chat_session_id to payload if it exists
    if request_data.chat_session_id and request_data.chat_session_id != uuid.UUID('00000000-0000-0000-0000-000000000000'):
        payload["sessionId"] = str(request_data.chat_session_id)
    else:
        payload["sessionId"] = str('')

    logger.info(f"bedrock query payload: {payload}")
    
    try:
        # Run the blocking Lambda invocation in a thread pool
        response = await run_in_threadpool(
            lambda: client.invoke(
                FunctionName='bd_base_query146',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
        )
        response_payload = json.loads(response['Payload'].read())

        # Extract the chat_session_id from the response
        chat_session_id = None
        response_body = json.loads(response_payload['body'])
        if "sessionId" in response_body:
            chat_session_id = UUID(response_body["sessionId"])
        elif request_data.chat_session_id:
            # Fallback to the provided session_id if not returned by lambda
            chat_session_id = request_data.chat_session_id
        
        # Log the LLM query
        if request:
            asyncio.create_task(log_llm_query(
                request=request,
                user_id=current_user.id,
                project_name=user_projects[0].name,
                query=request_data.query,
                db=db,
                chat_session_id=chat_session_id,
                model_id=model_id,
                response=response_payload
            ))

        # Add the chat_session_id to the response
        if chat_session_id:
            response_payload["chat_session_id"] = str(chat_session_id)

        return response_payload
    except ClientError as e:
        logger.error(f"An error occurred while invoking the Lambda function: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while invoking the Lambda function")

class CreateUserRequest(BaseModel):
    action: str
    emails: List[str]

@router.post("/create_user")
def manage_cognito_users(
    request: CreateUserRequest,
    current_user: PyUser = Depends(get_current_user),
):
    lambda_function_name = 'create_user73b'

    client = boto3.client('lambda')

    payload = {
        "action": request.action,
        "emails": request.emails
    }

    try:
        response = client.invoke(
            FunctionName=lambda_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        response_payload = json.loads(response['Payload'].read())
        
        user_obj = interface.get_or_create_item(UserCreate(email=request.emails[0]))

        if request.action == "delete":
            interface.delete_item(user_obj)
        
        return response_payload
    except ClientError as e:
        logger.error(f"Error invoking Lambda function '{lambda_function_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to invoke Create User Lambda function")

def get_s3_client():
    """
    Creates and returns an S3 client.
    """
    try:
        s3_client = boto3.client('s3')
        return s3_client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating S3 client: {e}")

@router.get("/admin/files")
def get_all_files(
    request: Request,
    current_user: PyUser = Depends(get_current_user),
    s3_client: boto3.client = Depends(get_s3_client),
):

    logger.log(level=logging.INFO, msg=request)
    
    if not (is_admin(current_user) or is_uploader(current_user)):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Get the S3 bucket for the user's project
        s3_bucket = get_s3_bucket_for_user_project(current_user)

        response = s3_client.list_objects_v2(Bucket=s3_bucket)
        files = []
        for item in response.get("Contents", []):
            files.append({
                "key": item["Key"],
                "lastModified": item["LastModified"].isoformat(),
                "size": item["Size"]
            })

        return files
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@router.post("/admin/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: PyUser = Depends(get_current_user),
    s3_client: boto3.client = Depends(get_s3_client),
    db: Any = Depends(get_db),
    request: Request = None
):
    if not (is_admin(current_user) or is_uploader(current_user)):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Get the S3 bucket for the user's project
    s3_bucket = get_s3_bucket_for_user_project(current_user)
    
    uploaded = []
    for file in files:
        try:
            # Get file size before uploading to S3
            file.file.seek(0, 2)  # Seek to the end of the file
            file_size = file.file.tell()  # Get current position (file size)
            file.file.seek(0)  # Reset file position to beginning for upload
            
            # S3 operations are blocking, run them in a thread pool
            await run_in_threadpool(
                lambda: s3_client.upload_fileobj(file.file, s3_bucket, file.filename)
            )
            
            # Create database entry for the file
            file_create = FileCreate(
                name=file.filename,
                type=os.path.splitext(file.filename)[1],
                s3_bucket=s3_bucket,
                s3_key=file.filename,
                storage_kind="s3",
                project_id=current_user.projects[0].id if current_user.projects else None
            )
            interface.get_or_create_item(file_create)
            
            uploaded.append(file.filename)
            
            # Log the file upload using the previously captured size
            if request:
                asyncio.create_task(log_file_operation(
                    request=request,
                    user_id=current_user.id,
                    operation="upload",
                    db=db,
                    file_details={
                        "filename": file.filename,
                        "bucket": s3_bucket,
                        "size": file_size
                    }
                ))
                
        except (ClientError) as e:
            logging.error(f"Upload failed: {file.filename}, error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")
    return {"uploaded": uploaded}

@router.get("/admin/delete")
async def delete_file(
    key: str,
    current_user: PyUser = Depends(get_current_user),
    s3_client: boto3.client = Depends(get_s3_client),
    request: Request = None,
    db: Any = Depends(get_db) 
):
    if not (is_admin(current_user) or is_uploader(current_user)):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not key:
        raise HTTPException(status_code=400, detail="Missing file key")

    try:
        # Get the S3 bucket for the user's project
        s3_bucket = get_s3_bucket_for_user_project(current_user)
        
        # Get file metadata before deletion
        try:
            file_metadata = s3_client.head_object(Bucket=s3_bucket, Key=key)
            # Convert datetime objects in metadata to ISO format strings
            serializable_metadata = {
                'ContentLength': file_metadata.get('ContentLength'),
                'ContentType': file_metadata.get('ContentType'),
                'LastModified': file_metadata.get('LastModified').isoformat() if file_metadata.get('LastModified') else None,
                'ETag': file_metadata.get('ETag'),
            }
        except ClientError:
            serializable_metadata = {}
        
        # S3 operations might be blocking, consider running in thread pool
        await run_in_threadpool(lambda: s3_client.delete_object(Bucket=s3_bucket, Key=key))
               
        # Delete from database
        file_to_delete = db.query(FileTable).filter(
            FileTable.s3_bucket == s3_bucket,
            FileTable.s3_key == key
        ).first()
        
        if file_to_delete:
            db.delete(file_to_delete)
            db.commit()
            
        # Log the file deletion
        if request:
            asyncio.create_task(log_file_operation(
                request=request,
                user_id=current_user.id,
                operation="delete",
                db=db,
                file_details={
                    "filename": key,
                    "bucket": s3_bucket,
                    "metadata": serializable_metadata,
                    "db_file_id": str(file_to_delete.id) if file_to_delete else None
                }
            ))
            
        return {"deleted": key}
    except (ClientError) as e:
        logging.error(f"Delete failed: {key}, error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")
    except Exception as e:
        logging.error(f"Database deletion failed: {key}, error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete file from database")

@router.get("/admin/signed_url")
def get_signed_url(key: str = Query(...),
    current_user: PyUser = Depends(get_current_user),
    s3_client: boto3.client = Depends(get_s3_client),):
    
    if not (is_admin(current_user) or is_uploader(current_user)):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Get the S3 bucket for the user's project
        s3_bucket = get_s3_bucket_for_user_project(current_user)
        
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket, "Key": key},
            ExpiresIn=timedelta(minutes=5).seconds,
        )
        return {"url": url}
    except (ClientError) as e:
        logging.error(f"Signed URL generation failed for {key}: {e}")
        raise HTTPException(status_code=500, detail="Could not generate signed URL")

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    has_more: bool

@router.get("/paginated_results")
def get_paginated_results(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None),
    current_user: PyUser = Depends(get_current_user),
):
    """Get paginated results with minimal data for table display."""
    try:
        # Get base results query
        results = interface.get_all(PyResult)
        
        # Filter results by user's projects
        results = [r for r in results if is_item_in_user_projects(r, current_user)]
        
        # Apply status filter if provided
        if status_filter:
            results = [r for r in results if r.answer == status_filter]

        # Calculate pagination
        total = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get slice of results for current page
        page_results = results[start_idx:end_idx]

        # Transform results to minimal data needed for table
        transformed_results = []
        for result in page_results:
            transformed_results.append({
                "id": str(result.id),
                "criterion": {
                    "question": result.criterion.question,
                    "category": result.criterion.category,
                    "gate": result.criterion.gate
                },
                "status": result.answer,
                "source_count": len(result.chunks)
            })

        return PaginatedResponse(
            items=transformed_results,
            total=total,
            has_more=end_idx < total
        )

    except Exception as e:
        logger.error(f"Error fetching paginated results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/result_details/{result_id}")
async def get_result_details(
    result_id: UUID,
    current_user: PyUser = Depends(get_current_user),
):
    """Get detailed result data including sources and ratings."""
    try:
        result = interface.get_by_id(PyResult, result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        
        if not is_item_in_user_projects(result, current_user):
            raise HTTPException(status_code=403, detail="Not authorized to view this result")

        # Get all sources for the chunks in parallel
        sources = []
        for chunk in result.chunks:
            source = interface.get_by_id(PyChunk, chunk.id)
            if source and source.file:
                sources.append({
                    "chunk_id": str(source.id),
                    "fileName": source.file.name
                })

        return {
            "id": str(result.id),
            "criterion": {
                "question": result.criterion.question,
                "evidence": result.criterion.evidence,
                "category": result.criterion.category,
                "gate": result.criterion.gate
            },
            "status": result.answer,
            "justification": result.full_text,
            "sources": sources,
            "ratings": [
                {
                    "id": str(rating.id),
                    "positive_rating": rating.positive_rating,
                    "created_datetime": rating.created_datetime,
                    "updated_datetime": rating.updated_datetime
                }
                for rating in result.ratings
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching result details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/audit-logs")
def get_audit_logs(
    request: Request,
    current_user: PyUser = Depends(get_current_user),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    action_type: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """Get paginated audit logs with optional filtering."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        # Base query
        audit_logs = interface.get_all(models.get("audit_log"))
        
        # Apply filters
        if start_date:
            audit_logs = [log for log in audit_logs if log.timestamp >= start_date]
        if end_date:
            audit_logs = [log for log in audit_logs if log.timestamp <= end_date]
        if action_type:
            audit_logs = [log for log in audit_logs if log.action_type == action_type]
        if user_id:
            audit_logs = [log for log in audit_logs if log.user_id == user_id]

        # Sort by timestamp descending
        audit_logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Calculate pagination
        total = len(audit_logs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get slice of logs for current page
        page_logs = audit_logs[start_idx:end_idx]

        return {
            "items": [log.dict() for log in page_logs],
            "total": total,
            "has_more": end_idx < total,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        logger.error(f"Error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_summary_data(
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db)
) -> dict:
    """Get consolidated summary data for the index page."""
    try:
        if not current_user.projects:
            return {
                "answer_count": {},
                "project": None,
                "gate_url": None
            }
            
        current_project_id = current_user.projects[0].id

        results = (
            db.query(SqResult)
            .join(SqCriterion)
            .join(SqProject)
            .filter(SqResult.project_id == current_project_id)
            .options(
                joinedload(SqResult.criterion),
                joinedload(SqResult.project)
            )
            .all()
        )
        
        # Get project details
        project = db.query(SqProject).filter(SqProject.id == current_project_id).first()

        # Process data
        answer_count = {}
        first_criterion_with_gate = None
        
        for result in results:
            # Count answers
            answer_count[result.answer] = answer_count.get(result.answer, 0) + 1
            
            # Find first criterion with gate
            if not first_criterion_with_gate and result.criterion and result.criterion.gate:
                first_criterion_with_gate = result.criterion
        
        return {
            "answer_count": answer_count,
            "project": {
                "id": str(project.id),  # Convert UUID to string
                "name": project.name,
                "results_summary": project.results_summary
            } if project else None,
            "gate_url": first_criterion_with_gate.gate if first_criterion_with_gate else None
        }
    except Exception as e:
        logger.exception("Error getting summary data: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-referenced-documents")
async def get_top_referenced_documents(
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
) -> dict:
    """Get top referenced documents based on how many results reference their chunks."""
    try:
        if not current_user.projects:
            return {
                "documents": [],
                "total": 0
            }
            
        current_project_id = current_user.projects[0].id

        # Query to get files and count how many results reference their chunks
        query = (
            db.query(
                SqFile.id,
                SqFile.name,
                SqFile.clean_name,
                SqFile.summary,
                SqFile.type,
                SqFile.created_datetime,
                func.count(SqResult.id.distinct()).label('reference_count')
            )
            .outerjoin(SqChunk, SqFile.id == SqChunk.file_id)
            .outerjoin(result_chunks, SqChunk.id == result_chunks.c.chunk_id)
            .outerjoin(SqResult, result_chunks.c.result_id == SqResult.id)
            .filter(SqFile.project_id == current_project_id)
            .group_by(SqFile.id, SqFile.name, SqFile.clean_name, SqFile.summary, SqFile.type, SqFile.created_datetime)
            .order_by(func.count(SqResult.id.distinct()).desc())
            .limit(limit)
        )
        
        results = query.all()
        
        documents = []
        for result in results:
            documents.append({
                "id": str(result.id),
                "name": result.name,
                "clean_name": result.clean_name or result.name,
                "summary": result.summary or "",
                "type": result.type,
                "reference_count": result.reference_count,
                "created_datetime": result.created_datetime.isoformat() if result.created_datetime else None
            })
        
        return {
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.exception("Error getting top referenced documents: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/update_user")
def update_user(
    associateUserToRoleRequest: AssociateUserToRoleRequest,
    current_user: PyUser = Depends(get_current_user),
):
    """Updates a user's role."""
    if not current_user.role or current_user.role.name != RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        user = interface.get_by_id(PyUser, associateUserToRoleRequest.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get the role from the role table
        role = interface.filter_items(RoleFilter(name=associateUserToRoleRequest.role), None)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
            
        updated_user = interface.update_item(
            UserUpdate(
                id=user.id,
                email=user.email,
                updated_datetime=datetime.utcnow(),
                role_id=role[0].id
            )
        )
        return updated_user
    
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating user: {e}")

def is_admin(user: PyUser) -> bool:
    return user.role and user.role.name == RoleEnum.ADMIN

def is_uploader(user: PyUser) -> bool:
    return user.role and user.role.name == RoleEnum.UPLOADER

@router.get("/chat-history")
def get_chat_history(
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db),
    session_id: Optional[UUID] = Query(None, description="Filter by specific chat session ID")
):
    try:
        # Create a query that joins ChatSession and AuditLog tables
        query = (
            select(AuditLog)
            .join(
                ChatSession, 
                AuditLog.chat_session_id == ChatSession.id, 
                isouter=True
            )
            .where(
                and_(
                    AuditLog.user_id == current_user.id,
                    AuditLog.action_type == 'llm_query'
                )
            )
        )
        
        # Filter by session_id if provided
        if session_id:
            query = query.where(AuditLog.chat_session_id == session_id)
            
        # Order by timestamp descending
        query = query.order_by(AuditLog.timestamp)
        
        # Execute the query
        result = db.execute(query).scalars().all()
        
        # Process the result into a list of dictionaries
        chat_history = []
        for log in result:
            try:
                # Process the details JSON
                details = log.details if isinstance(log.details, dict) else {}
                query_text = details.get("query", "Unknown query")
                
                # Extract response from the nested structure
                response_data = details.get("response", {})
                if isinstance(response_data, dict):
                    response_body = response_data.get("body", "{}")
                    # The response body might be a JSON string that needs parsing
                    if isinstance(response_body, str):
                        try:
                            response_body_json = json.loads(response_body)
                            response_text = response_body_json.get("response", "Unknown response")
                        except json.JSONDecodeError:
                            response_text = response_body
                    else:
                        response_text = response_body.get("response", "Unknown response")
                else:
                    response_text = "Unknown response"
                
                chat_history.append({
                    "id": str(log.id),
                    "query": query_text,
                    "response": response_text,
                    "timestamp": log.timestamp.isoformat(),
                    "session_id": str(log.chat_session_id) if log.chat_session_id else None
                })
            except Exception as e:
                logger.error(f"Error parsing details for log {log.id}: {e}")
                chat_history.append({
                    "id": str(log.id),
                    "query": "Error parsing query",
                    "response": "Error parsing response",
                    "timestamp": log.timestamp.isoformat(),
                    "session_id": str(log.chat_session_id) if log.chat_session_id else None
                })
        
        return chat_history
        
    except Exception as e:
        logger.exception("Error fetching chat history")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching chat history: {str(e)}"
        )

@router.get("/chat-sessions")
def get_chat_sessions(
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Get all chat sessions for the current user in their current project."""
    try:
        # Check if user has any projects
        if not current_user.projects:
            return []
            
        # Get the current project ID
        current_project_id = current_user.projects[0].id
        
        # Query all non-deleted chat sessions for the current user in the current project
        query = (
            select(ChatSession)
            .where(and_(
                ChatSession.user_id == current_user.id,
                ChatSession.project_id == current_project_id,
                ChatSession.deleted == False
            ))
            .order_by(ChatSession.updated_datetime.desc())
        )
        
        # Execute the query
        result = db.execute(query).scalars().all()
        
        # Transform the result
        sessions = []
        for session in result:
            # Count messages in this session
            message_count_query = (
                select(func.count())
                .select_from(AuditLog)
                .where(
                    and_(
                        AuditLog.chat_session_id == session.id,
                        AuditLog.action_type == 'llm_query'
                    )
                )
            )
            message_count = db.execute(message_count_query).scalar()
            
            sessions.append({
                "id": str(session.id),
                "title": session.title,
                "created_datetime": session.created_datetime.isoformat(),
                "updated_datetime": session.updated_datetime.isoformat() if session.updated_datetime else None,
                "message_count": message_count,
                "project_id": str(session.project_id) if session.project_id else None
            })
            
        return sessions
        
    except Exception as e:
        logger.exception("Error fetching chat sessions")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching chat sessions: {str(e)}"
        )

@router.post("/chat-sessions")
def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Create a new chat session."""
    try:
        # Check if user has a project
        if not current_user.projects:
            raise HTTPException(status_code=400, detail="User has no projects")

        session_id_to_use = session_data.id if session_data.id else uuid.uuid4()
        
        # Optional: Check if a session with this ID already exists for this user/project
        # existing_session = db.query(ChatSession).filter(ChatSession.id == session_id_to_use).first()
        # if existing_session:
        #     raise HTTPException(status_code=409, detail=f"Session with ID {session_id_to_use} already exists.")

        new_session = ChatSession(
            id=session_id_to_use,
            created_datetime=datetime.utcnow(),
            updated_datetime=datetime.utcnow(),
            title=session_data.title,
            user_id=current_user.id,
            project_id=current_user.projects[0].id,
            deleted=False
        )

        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        return {
            "id": str(new_session.id),
            "title": new_session.title,
            "created_datetime": new_session.created_datetime.isoformat(),
            "message_count": 0
        }
        
    except Exception as e:
        db.rollback()
        logger.exception("Error creating chat session")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating chat session: {str(e)}"
        )

@router.put("/chat-sessions/{session_id}")
def update_chat_session(
    session_id: UUID,
    session_data: ChatSessionUpdate,
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Update a chat session title."""
    try:
        # Find the session
        session = db.query(ChatSession).filter(
            and_(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id,
                ChatSession.deleted == False
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Update the session
        if session_data.title:
            session.title = session_data.title
        if session_data.deleted is not None:
            session.deleted = session_data.deleted
        
        session.updated_datetime = datetime.utcnow()
        
        db.commit()
        db.refresh(session)
        
        return {
            "id": str(session.id),
            "title": session.title,
            "created_datetime": session.created_datetime.isoformat(),
            "updated_datetime": session.updated_datetime.isoformat() if session.updated_datetime else None,
            "deleted": session.deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error updating chat session")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while updating chat session: {str(e)}"
        )

@router.delete("/chat-sessions/{session_id}")
def delete_chat_session(
    session_id: UUID,
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db)
):
    """Soft delete a chat session by marking it as deleted."""
    try:
        # Find the session
        session = db.query(ChatSession).filter(
            and_(
                ChatSession.id == session_id,
                ChatSession.user_id == current_user.id
            )
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Soft delete the session
        session.deleted = True
        session.updated_datetime = datetime.utcnow()
        db.commit()
        
        return {"message": "Chat session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error deleting chat session")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting chat session: {str(e)}"
        )

@router.get("/user/role")
def get_user_role(
    current_user: PyUser = Depends(get_current_user),
):
    """Get the current user's role and project info."""
    try:
        # Get project info if available
        project_info = None
        if current_user.projects and len(current_user.projects) > 0:
            project = current_user.projects[0]  # Get first project
            project_info = {
                "id": str(project.id),
                "name": project.name
            }
            
        return {
            "role": current_user.role.name if current_user.role else None,
            "user_id": str(current_user.id),
            "project": project_info
        }
    except Exception as e:
        logger.error(f"Error fetching user role: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching user role: {e}")
