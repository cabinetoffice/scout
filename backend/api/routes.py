import base64
from datetime import datetime, timedelta
import json
import logging
import typing
from functools import lru_cache
from typing import Annotated, List, Any
from typing import Optional
from uuid import UUID
from sqlalchemy import select
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
    AuditLog,
)
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
    "audit_log": AuditLog,
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
    
    if current_user.role != "admin":
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
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        projects = interface.filter_items(ProjectFilter(), current_user)

        return projects
    except Exception as e:
        logger.error(f"Error fetching all projects: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching all projects: {e}")

@router.post("/custom-query")
async def custom_query(
    query: str,
    current_user: PyUser = Depends(get_current_user),
    request: Request = None,
):
    model_id = os.getenv("AWS_BEDROCK_MODEL_ID")

    user_projects = current_user.projects
    if not user_projects:
        raise HTTPException(status_code=404, detail="No projects found for the current user.")
    
    knowledge_id = user_projects[0].knowledgebase_id or os.getenv("AWS_BEDROCK_KB_ID")
    
    if not model_id or not knowledge_id:
        raise HTTPException(status_code=500, detail="Model ID or Knowledge ID not found in environment variables or project table")

    client = boto3.client('lambda')

    payload = {
        "query": str(query),
        "modelId": str(model_id),
        "knowledgeBaseId": str(knowledge_id)
    }

    logger.info(f"bedrock query payload: {payload}")
    
    try:
        # Run the blocking Lambda invocation in a thread pool
        response = await run_in_threadpool(
            lambda: client.invoke(
                FunctionName='bd_base_query145',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
        )
        response_payload = json.loads(response['Payload'].read())
        
        # Log the LLM query
        if request:
            asyncio.create_task(log_llm_query(
                request=request,
                user_id=current_user.id,
                project_name=user_projects[0].name,
                query=query,
                response=response_payload
            ))
        
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
    
    if current_user.role != "admin":
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
    request: Request = None
):
    if current_user.role != "admin":
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
    if current_user.role != "admin":
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
    
    if current_user.role != "admin":
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
    if current_user.role != "admin":
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
