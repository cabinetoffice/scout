"""
This script evaluates documents stored in an AWS Bedrock Knowledge Base against 
specified criteria using an LLM, without first ingesting them into the Scout system.

The evaluation results are saved to a Postgres database, and can then be viewed 
in the Scout frontend. This allows organisations to keep their documents in 
AWS Bedrock Knowledge Base while still using Scout for assessment.

See the project README for instructions on how to run.
"""

import datetime
import os
import json
import uuid
import boto3
from botocore.client import Config

from dotenv import load_dotenv
from typing import List, Dict, Any

from langchain_aws import ChatBedrock
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

from scout.DataIngest.models.schemas import Chunk, ChunkCreate, CriterionGate, FileCreate, ProjectCreate
from scout.Pipelines.ingest_criteria import ingest_criteria_from_local_dir
from scout.LLMFlag.evaluation import MainEvaluator
from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler
from scout.utils.utils import logger

from scout.DataIngest.models.schemas import (
    Criterion,
    CriterionCreate,
    CriterionFilter,
    CriterionGate,
    ProjectCreate,
    ProjectFilter,
    ResultCreate,
)

load_dotenv()


def evaluate_kb_against_criteria(
    kb_id: str,
    project_name: str,
    gate_review: CriterionGate,
    storage_handler: PostgresStorageHandler,
    criteria_csv_list: List[str],
    region_name: str = None,
    model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID"),
    max_results: int = 5
) -> None:
    """
    Evaluate an AWS Bedrock Knowledge Base against criteria using LangChain's AmazonKnowledgeBasesRetriever

    Args:
        kb_id: AWS Bedrock Knowledge Base ID
        project_name: Name to use for the project in the database
        gate_review: Gate review type (e.g., GATE_2, GATE_3)
        storage_handler: Database storage handler
        criteria_csv_list: List of CSV files containing criteria
        region_name: AWS region name (defaults to session region)
        model_id: AWS Bedrock model ID to use
        max_results: Maximum number of results to return per query
    """
    # Initialize AWS session and clients
    session = boto3.session.Session()
    region = region_name or session.region_name

    bedrock_config = Config(
        connect_timeout=120, read_timeout=120, retries={'max_attempts': 0}
    )
    bedrock_client = boto3.client(
        'bedrock-runtime', region_name=region, config=bedrock_config)

    # Initialize LangChain components
    llm = ChatBedrock(
        model_id=model_id,
        client=bedrock_client
    )

    # Initialize the AmazonKnowledgeBasesRetriever
    retriever = AmazonKnowledgeBasesRetriever(
        knowledge_base_id=kb_id,
        retrieval_config={
            "vectorSearchConfiguration": {
                "numberOfResults": max_results,
                "overrideSearchType": "HYBRID",  # Using hybrid search
            }
        },
    )

    # Ingest criteria from CSVs
    ingest_criteria_from_local_dir(
        gate_filepaths=criteria_csv_list, storage_handler=storage_handler)
    logger.info("Criteria ingested")

    # Create project in database
    project = ProjectCreate(
        name=project_name
    )
    project = storage_handler.write_item(project)
    logger.info(f"Created project: {project.name}")

    # Get criteria for gate
    filter = CriterionFilter(gate=gate_review)
    criteria = storage_handler.get_item_by_attribute(filter)
    logger.info(f"{len(criteria)} criteria loaded")

    # Create custom MainEvaluator that uses KB for retrieval
    class KBMainEvaluator(MainEvaluator):
        def semantic_search(self, query: str, k: int, filters: dict):
            # Use LangChain retriever instead of custom KB implementation
            documents = retriever.get_relevant_documents(query)

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
                    print("S3 bucket or key not found in metadata.")
                    return None

                file_name = object_key.split("/")[-1]

                file_create = FileCreate(
                    name=file_name,
                    s3_key=object_key,
                    type=os.path.splitext(file_name)[1],
                    project=project,
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
                        'uuid': created_chunk.id,  # str(uuid.uuid4()),
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
        llm=llm,  # Use the LangChain LLM we initialized
        storage_handler=storage_handler
    )

    # Evaluate criteria
    results = evaluator.evaluate_questions(criteria=criteria, save=True)
    logger.info(f"Evaluated {len(results)} criteria against Knowledge Base")

    # Generate summary and save to project
    summary = evaluator.generate_summary(
        [(c.question, r.full_text) for c, r in zip(criteria, results)])
    project.results_summary = summary
    storage_handler.update_item(project)
    logger.info("Evaluation complete")


if __name__ == "__main__":
    # These are your settings
    kb_id = os.getenv("AWS_BEDROCK_KB_ID", "")  # AWS Bedrock Knowledge Base ID
    project_name = "bedrock_kb_project" + "-" + \
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    gate_review = CriterionGate.GATE_3  # Criteria to review against
    criteria_csv_list = [
        ".data/criteria/example_2.csv",
        ".data/criteria/example_3.csv",
    ]

    # Initialize database handler
    storage_handler = PostgresStorageHandler()

    # Run evaluation
    evaluate_kb_against_criteria(
        kb_id=kb_id,
        project_name=project_name,
        gate_review=gate_review,
        storage_handler=storage_handler,
        criteria_csv_list=criteria_csv_list
    )
