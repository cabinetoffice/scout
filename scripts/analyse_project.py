#!/usr/bin/env python
"""
This script evaluates documents stored in an AWS Bedrock Knowledge Base against 
specified criteria using an LLM, without first ingesting them into the Scout system.

The evaluation results are saved to a Postgres database, and can then be viewed 
in the Scout frontend. This allows organisations to keep their documents in 
AWS Bedrock Knowledge Base while still using Scout for assessment.

See the project README for instructions on how to run.
"""

import argparse
import os
import sys
import typing

import boto3
from botocore.client import Config
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_community.retrievers import AmazonKnowledgeBasesRetriever

from scout.DataIngest.models.schemas import (
    CriterionFilter,
    CriterionGate, ChunkCreate,
)
from scout.utils.storage.postgres_models import File
from scout.DataIngest.models.schemas import Project, ProjectFilter
from scout.LLMFlag.evaluation import MainEvaluator
from scout.LLMFlag.prompts import DOCUMENT_EXTRACTS_HEADER, DOCUMENT_EXTRACT_PROMPT
from scout.utils.storage.postgres_interface import SessionManager
from scout.utils.utils import logger

if typing.TYPE_CHECKING:
    from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler


load_dotenv()


def evaluate_kb_against_criteria(
    project: Project,
    gate_review: CriterionGate,
    storage_handler: "PostgresStorageHandler",
    region_name: str = None,
    model_id: str = os.getenv("AWS_BEDROCK_MODEL_ID"),
    max_results: int = 5
) -> None:
    """
    Evaluate an AWS Bedrock Knowledge Base against criteria using LangChain's AmazonKnowledgeBasesRetriever

    Args:
        project_name: Name to use for the project in the database
        gate_review: Gate review type (e.g., GATE_2, GATE_3)
        storage_handler: Database storage handler
        region_name: AWS region name (defaults to session region)
        model_id: AWS Bedrock model ID to use
        max_results: Maximum number of results to return per query
    """
    # Initialize AWS session and clients
    session = boto3.session.Session()
    region = region_name or session.region_name

    bedrock_config = Config(
        connect_timeout=120,
        read_timeout=120,
        retries={'max_attempts': 5},
        max_pool_connections=20
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
        knowledge_base_id=project.knowledgebase_id,
        retrieval_config={
            "vectorSearchConfiguration": {
                "numberOfResults": max_results,
                "overrideSearchType": "HYBRID",  # Using hybrid search
            }
        },
    )

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
            prompt = DOCUMENT_EXTRACTS_HEADER
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

                with SessionManager() as db:
                    query = db.query(File)
                    query = query.filter(
                        File.s3_bucket == bucket_name,
                        File.s3_key == object_key,
                        File.project_id == project.id
                    )
                    file = query.one()

                source = doc.metadata.get('source', 'Unknown')
                content = doc.page_content

                # Create document ID from source or use a default
                doc_id = source.split('/')[-1] if source else f"document_{i+1}"

                prompt += DOCUMENT_EXTRACT_PROMPT.format(
                    file_name=getattr(file, "clean_name", file.name),
                    source=getattr(file, "source", None),
                    summary=getattr(file, "summary", None),
                    date=getattr(file, "published_date", None),
                    text=doc.page_content,
                )

                chunk = ChunkCreate(
                    file=file,
                    idx=0,
                    text=doc.page_content,
                    page_num=source_metadata.get("x-amz-bedrock-kb-document-page-number", 0)
                )
                created_chunk = self.storage_handler.write_item(chunk)

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
    parser = argparse.ArgumentParser(
        prog="analyse_project",
        description="Analyse a project according to NISTA criteria.",
    )

    parser.add_argument(
        "project_name",
        help="The name of the project in the Scout database. "
        "This must have been created during the ingestion by ingest_project.py script."
    )
    parser.add_argument(
        "-g", "--gate-review",
        help="The set of criteria to review against. " +
             f"Correct values: {', '.join(CriterionGate.__members__)}.",
        type=CriterionGate,
        default=CriterionGate.GATE_3
    )

    args = parser.parse_args()

    # Initialize database handler
    from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler
    storage_handler = PostgresStorageHandler()

    # Get the project
    project_filter = ProjectFilter(name=args.project_name)
    project_list = storage_handler.get_item_by_attribute(project_filter)
    if not project_list:
        print(f"Project {args.project_name} was not found.", file=sys.stderr)
        sys.exit(1)

    # Run evaluation
    evaluate_kb_against_criteria(
        project=project_list[0],
        gate_review=args.gate_review,
        storage_handler=storage_handler
    )
