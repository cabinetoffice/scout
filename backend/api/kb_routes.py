import datetime
import json
import os
import uuid
from typing import List, Dict, Any, Optional

import boto3
from botocore.client import Config
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Query, Request

from langchain_aws import ChatBedrock
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever
from pydantic import BaseModel

from backend.utils.custom_query_request import CustomQueryRequest
from scout.DataIngest.models.schemas import (
    ChunkCreate,
    Criterion,
    CriterionCreate,
    CriterionFilter,
    CriterionGate,
    FileCreate,
    ProjectCreate,
    ProjectFilter,
    ResultCreate,
    ProjectUpdate,
    ResultFilter,
    Project,
    User as PyUser
)
from scout.Pipelines.ingest_criteria import ingest_criteria_from_local_dir, ingest_criteria_from_s3
from scout.LLMFlag.evaluation import MainEvaluator
from scout.utils.llm_formats import format_llm_request
from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler
from scout.utils.storage.postgres_models import Criterion as SqCriterion
from scout.utils.utils import logger
from backend.api.routes import get_current_user, get_db
from starlette.concurrency import run_in_threadpool


load_dotenv()

router = APIRouter()


class EvaluationRequest(BaseModel):
    kb_id: str
    project_name: str
    gate_review: CriterionGate
    criteria_csv_list: List[str]
    region_name: str = None
    model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID")
    max_results: int = 5


def get_storage_handler():
    return PostgresStorageHandler()

@router.post("/ingest/")
async def ingest(
    request: EvaluationRequest, storage_handler: PostgresStorageHandler = Depends(get_storage_handler)
):
    """
    Evaluate an AWS Bedrock Knowledge Base against criteria.
    """
    try:
        # Initialize AWS session and clients
        session = boto3.session.Session()
        region = request.region_name or session.region_name

        criteria_csv_list = [
        "criteria/example_2.csv",
        "criteria/example_3.csv",
    ]
            
        ingest_criteria_from_s3(
            gate_filepaths=criteria_csv_list,
            storage_handler=storage_handler, region_name=region)

        return {"message": "Ingestion completed successfully"}
    
    except Exception as e:
        logger.error(f"Error during ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ProcessCriteriaRequest(BaseModel):
    criterion_id: Optional[uuid.UUID] = None
    model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID")
    max_results: int = 5

@router.post("/process-criteria")
async def process_criteria(
    request_data: ProcessCriteriaRequest,
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db),
    storage_handler: PostgresStorageHandler = Depends(get_storage_handler)
):
    """
    Process specific criteria or all unprocessed criteria for the user's current project
    and store results in the database.
    """
    try:
        # Check if user has any projects
        if not current_user.projects:
            raise HTTPException(status_code=404, detail="User does not have any projects")
            
        # Get the current project
        current_project = current_user.projects[0]
        project_id = current_project.id
        kb_id = current_project.knowledgebase_id
        
        if not kb_id:
            raise HTTPException(status_code=400, detail="Project does not have a knowledgebase ID")
        
        # Initialize AWS session and clients
        session = boto3.session.Session()
        region = session.region_name

        bedrock_config = Config(
            connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}
        )
        bedrock_client = boto3.client(
            'bedrock-runtime', region_name=region, config=bedrock_config)

        # Initialize LangChain components
        llm = ChatBedrock(
            model_id=request_data.model_id,
            client=bedrock_client
        )

        # Initialize the AmazonKnowledgeBasesRetriever
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=kb_id,
            retrieval_config={
                "vectorSearchConfiguration": {
                    "numberOfResults": request_data.max_results,
                    "overrideSearchType": "HYBRID",
                }
            },
        )
        
        # Get the project from the database using the storage handler
        project_filter = ProjectFilter(id=project_id)
        project_list = storage_handler.get_item_by_attribute(project_filter)
        
        if not project_list:
            raise HTTPException(status_code=404, detail="Project not found in database")
            
        project = project_list[0]
        
        # If a specific criterion ID is provided, only process that one
        if request_data.criterion_id:
            filter = CriterionFilter(id=request_data.criterion_id)
            criteria = storage_handler.get_item_by_attribute(filter)
            if not criteria:
                raise HTTPException(status_code=404, detail="Criterion not found")
        else:
            # Get criteria without results for the current project
            criteria = get_criteria_without_results(project, storage_handler)
            
        if not criteria:
            return {"message": "No criteria to process", "processed": 0}
        
        logger.info(f"Processing {len(criteria)} criteria for project {project.name}")
        
        # Create custom MainEvaluator that uses KB for retrieval
        class KBMainEvaluator(MainEvaluator):
            def semantic_search(self, query: str, k: int, filters: dict):
                # Use LangChain retriever instead of custom KB implementation
                logger.info(f"Query: {query}")
                documents = retriever.get_relevant_documents(query)
                logger.info(f"Number of relevant documents: {len(documents)}")

                # Format into expected prompt structure
                prompt = "Document extracts relevant to the query:\n\n"
                formatted_docs = []

                for i, doc in enumerate(documents):
                    # Extract source_metadata dictionary
                    source_metadata = doc.metadata.get('source_metadata', {})
                    source_uri = source_metadata.get('x-amz-bedrock-kb-source-uri')

                    # Parse the S3 URI
                    bucket_name = source_uri.split('/')[2]
                    object_key = '/'.join(source_uri.split('/')[3:])
                    if not bucket_name or not object_key:
                        logger.warning("S3 bucket or key not found in metadata")
                        continue

                    file_name = object_key.split("/")[-1]

                    file_create = FileCreate(
                        name=file_name,
                        s3_key=object_key,
                        type=os.path.splitext(file_name)[1],
                        project_id=project.id,
                        s3_bucket=os.environ["BUCKET_NAME"],
                    )
                    file = self.storage_handler.write_item(file_create)

                    chunk = ChunkCreate(
                        file=file,
                        idx=0,
                        text=object_key,
                        page_num=0,
                    )

                    created_chunk = self.storage_handler.write_item(chunk)

                    source = doc.metadata.get('source', 'Unknown')
                    content = doc.page_content

                    # Create document ID from source or use a default
                    doc_id = source.split('/')[-1] if source else f"document_{i+1}"

                    prompt += f"Document {i+1}: {doc_id}\n"
                    prompt += f"Content: {content}\n\n"

                    # Format documents for return value
                    formatted_docs.append({
                        'content': content,
                        'metadata': {
                            'uuid': created_chunk.id,
                            'source': source,
                            'document_id': doc_id,
                            'score': doc.metadata.get('score', 0),
                            'file_id': file.id
                        }
                    })

                return prompt, formatted_docs

            def get_llm_response(self, messages):
                # Override to use the LangChain LLM
                response = llm.invoke(messages)
                return response.content

        # Initialize evaluator
        evaluator = KBMainEvaluator(
            project=project,
            vector_store=None,  # Not used with KB
            llm=llm,
            storage_handler=storage_handler
        )

        # Evaluate criteria
        results = evaluator.evaluate_questions(criteria=criteria, save=True)
        logger.info(f"Evaluated {len(results)} criteria against Knowledge Base")

        # Update the project summary if needed
        if not request_data.criterion_id:  # Only update summary if processing all criteria
            fresh_criteria = storage_handler.get_item_by_attribute(CriterionFilter(project_id=project.id))
            fresh_results = storage_handler.get_item_by_attribute(ResultFilter(project=project.id))

            criteria_results_pairs = [
                (criterion.question, result.full_text)
                for criterion in fresh_criteria
                for result in fresh_results
                if criterion.id == result.criterion.id
            ]
            
            # Only generate summary if we have results
            if criteria_results_pairs:
                summary = evaluator.generate_summary(criteria_results_pairs)
                
                project_update = ProjectUpdate(
                    id=project.id,
                    name=project.name,
                    results_summary=summary
                )
                storage_handler.update_item(project_update)

        return {
            "message": "Criteria processed successfully", 
            "processed": len(results),
            "project_id": str(project.id)
        }
        
    except Exception as e:
        logger.exception(f"Error processing criteria: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def get_criteria_without_results(project: Project, storage_handler: PostgresStorageHandler) -> List[Criterion]:
    """
    Get criteria that don't have associated results for the given project.
    """
    # Get all criteria for the project
    filter = CriterionFilter(project_id=project.id)
    all_criteria = storage_handler.get_item_by_attribute(filter)
    
    # Get all results for the project
    results_filter = ResultFilter(project=project.id)
    existing_results = storage_handler.get_item_by_attribute(results_filter)
    
    # Get set of criterion IDs that have results
    criterion_ids_with_results = {result.criterion.id for result in existing_results}
    
    # Filter criteria to only those without results
    criteria_without_results = [
        criterion for criterion in all_criteria 
        if criterion.id not in criterion_ids_with_results
    ]
    
    return criteria_without_results


class CreateProjectRequest(BaseModel):
    """Request schema for creating a new project."""
    project_name: str
    knowledgebase_id: str

@router.post("/projects")
async def create_project(
    request_data: CreateProjectRequest,
    current_user: PyUser = Depends(get_current_user),
    storage_handler: PostgresStorageHandler = Depends(get_storage_handler)
):
    """
    Create a new project with a specified name and knowledgebase ID.
    
    Args:
        request_data: CreateProjectRequest containing project_name and knowledgebase_id
        current_user: The authenticated user
        storage_handler: Database handler
        
    Returns:
        Project details if creation is successful
    """
    try:
        # Validate inputs
        if not request_data.project_name.strip():
            raise HTTPException(status_code=400, detail="Project name cannot be empty")
        
        if not request_data.knowledgebase_id.strip():
            raise HTTPException(status_code=400, detail="Knowledgebase ID cannot be empty")
            
        # Check if a project with the same name already exists for this user
        existing_projects = storage_handler.get_item_by_attribute(
            ProjectFilter(name=request_data.project_name)
        )
        
        # If projects with the same name exist, check if any belong to the current user
        if existing_projects:
            for project in existing_projects:
                # Check if the project is associated with the current user
                if str(project.user_id) == str(current_user.id):
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Project with name '{request_data.project_name}' already exists"
                    )
        
        # Create a new project
        project_create = ProjectCreate(
            name=request_data.project_name,
            knowledgebase_id=request_data.knowledgebase_id,
            user_id=current_user.id,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now()
        )
        
        # Save the project to the database
        new_project = storage_handler.write_item(project_create)
        
        logger.info(f"Created project: {new_project.name} with KB ID: {request_data.knowledgebase_id}")

        # Return the created project details
        return {
            "id": str(new_project.id),
            "name": new_project.name,
            "knowledgebase_id": request_data.knowledgebase_id,
            "created_at": new_project.created_at.isoformat() if hasattr(new_project, "created_at") else None,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        # If it's already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise
        # Otherwise, wrap it in an HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.post("/custom-query-context")
async def custom_query_context(
    request_data: CustomQueryRequest,
    criterion_id: uuid.UUID = Query(None, description="ID of the criterion to use for context"),
    current_user: PyUser = Depends(get_current_user),
    db: Any = Depends(get_db),
    request: Request = None
):
    """
    Process a custom query using the same context as the Bedrock evaluator for a given criterion.
    
    This endpoint retrieves relevant documents using the same mechanism as the analyse_project.py
    script, formats them in the same way, and then passes them to the LLM along with the user's query.
    
    Args:
        request_data: The custom query request
        criterion_id: Optional criterion ID to retrieve question context
        current_user: The authenticated user
        db: Database session
        request: The original HTTP request
    """
    try:
        # Get model_id from request or use default
        model_id = request_data.model_id or os.getenv("AWS_BEDROCK_MODEL_ID")
        
        # Get user's project
        user_projects = current_user.projects
        if not user_projects:
            raise HTTPException(status_code=404, detail="No projects found for the current user.")
        
        # Get knowledge base ID from project
        knowledge_id = user_projects[0].knowledgebase_id
        if not knowledge_id:
            raise HTTPException(status_code=500, detail="Knowledge Base ID not found in project")
        
        # Initialize AWS clients
        session = boto3.session.Session()
        region = session.region_name
        
        # Create the retriever
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=knowledge_id,
            retrieval_config={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,  # Same as in analyse_project.py
                    "overrideSearchType": "HYBRID",
                }
            },
        )
        
        # Prepare the query
        query_text = request_data.query
        
        # If a criterion ID is provided, add the criterion question to the query for better context
        if criterion_id:
            # Get the criterion from database
            criterion = None
            criterion_query = db.query(SqCriterion).filter(SqCriterion.id == criterion_id).first()
            if criterion_query:
                criterion = criterion_query

            if criterion:
                # Include criterion question for better context retrieval
                enhanced_query = f"Criterion: {criterion.question}\nUser query: {query_text}"
                logger.info(f"Enhanced query with criterion context: {enhanced_query}")
                query_text = enhanced_query
        
        # Use retriever to get documents
        logger.info(f"Retrieving documents for query: {query_text}")
        documents = retriever.get_relevant_documents(query_text)
        logger.info(f"Retrieved {len(documents)} documents for context")
        
        # Format documents into prompt format, just like in analyse_project.py
        prompt_context = "Document extracts relevant to the query:\n\n"
        
        for i, doc in enumerate(documents):
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content
            
            # Create document ID from source or use a default
            doc_id = source.split('/')[-1] if source else f"document_{i+1}"
            
            prompt_context += f"Document {i+1}: {doc_id}\n"
            prompt_context += f"Content: {content}\n\n"
        
        # Combine context with user query
        final_prompt = f"{prompt_context}\nQuestion: {request_data.query}\n\nAnswer:"
        
        # Format request for the LLM
        formatted_request = format_llm_request(
            model_id=model_id,
            prompt=final_prompt,
            max_tokens=1000
        )
        
        # Prepare payload for Lambda
        payload = {
            "query": str(formatted_request),
            "modelId": str(model_id),
            "knowledgeBaseId": str(knowledge_id)
        }
        
        logger.info(f"Sending custom query with context to LLM")
        
        # Invoke Lambda function
        client = boto3.client('lambda')
        response = await run_in_threadpool(
            lambda: client.invoke(
                FunctionName='bd_base_query145',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
        )
        
        # Process response
        response_payload = json.loads(response['Payload'].read())
        
        # # Log the LLM query
        # if request:
        #     asyncio.create_task(log_llm_query(
        #         request=request,
        #         user_id=current_user.id,
        #         project_name=user_projects[0].name,
        #         query=request_data.query,
        #         db=db,
        #         chat_session_id=request_data.chat_session_id,
        #         model_id=model_id,
        #         response=response_payload
        #     ))
        
        # Return response to client
        return {
            "response": response_payload.get("response"),
            "context": {
                "documents_used": len(documents),
                "criterion_id": str(criterion_id) if criterion_id else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in custom-query-context: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the query with context: {str(e)}"
        )