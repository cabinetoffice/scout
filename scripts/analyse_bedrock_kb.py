"""
This script evaluates documents stored in an AWS Bedrock Knowledge Base against 
specified criteria using an LLM, without first ingesting them into the Scout system.

The evaluation results are saved to a Postgres database, and can then be viewed 
in the Scout frontend. This allows organizations to keep their documents in 
AWS Bedrock Knowledge Base while still using Scout for assessment.

See the project README for instructions on how to run.
"""

import os
import json
import boto3

from dotenv import load_dotenv
from typing import List, Dict, Any

from scout.DataIngest.models.schemas import CriterionGate, ProjectCreate
from scout.Pipelines.ingest_criteria import ingest_criteria_from_local_dir
from scout.LLMFlag.evaluation import MainEvaluator
from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler
from scout.utils.utils import logger

load_dotenv()


class BedrockKnowledgeBase:
    """Interface for AWS Bedrock Knowledge Base operations"""
    
    def __init__(self, 
                 kb_id: str, 
                 retriever_id: str,
                 region_name: str = None):
        """
        Initialize Bedrock Knowledge Base client
        
        Args:
            kb_id: AWS Bedrock Knowledge Base ID
            retriever_id: Knowledge Base retriever ID
            region_name: AWS region name (defaults to env var)
        """
        self.kb_id = kb_id
        self.retriever_id = retriever_id
        self.region_name = region_name or os.getenv("AWS_REGION")
        
        # Initialize AWS clients
        self.bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=self.region_name
        )
        self.bedrock_agent = boto3.client(
            service_name="bedrock-agent",
            region_name=self.region_name
        )
    
    def retrieve(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents from Knowledge Base based on a query
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of documents with their content and metadata
        """
        try:
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.kb_id,
                retrieverId=self.retriever_id,
                retrievalQuery={
                    'text': query
                },
                maxResults=max_results
            )
            
            # Extract and format the retrieval results
            documents = []
            for result in response.get('retrievalResults', []):
                content = result.get('content', {}).get('text', '')
                metadata = {
                    'source': result.get('location', {}).get('s3Location', {}).get('uri', ''),
                    'score': result.get('score', 0),
                    'document_id': result.get('location', {}).get('type', '') + '/' + 
                                   result.get('location', {}).get('s3Location', {}).get('uri', '').split('/')[-1]
                }
                documents.append({
                    'content': content,
                    'metadata': metadata
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error retrieving from Knowledge Base: {str(e)}")
            raise
    
    def query_with_llm(self, query: str, system_prompt: str = None) -> str:
        """
        Query the Knowledge Base and use Bedrock model to generate a response
        
        Args:
            query: The user query
            system_prompt: Optional system prompt to guide the model
            
        Returns:
            Model-generated response
        """
        try:
            # First retrieve relevant documents
            documents = self.retrieve(query)
            
            # Format documents for context
            context = "\\n\\n".join([
                f"Document: {doc.get('metadata', {}).get('document_id', 'Unknown')}"
                f"\\n{doc.get('content', '')}" 
                for doc in documents
            ])
            
            # Create default system prompt if none provided
            if not system_prompt:
                system_prompt = (
                    "You are a helpful assistant. Answer the user's question based on the provided context. "
                    "If you cannot find the answer in the context, say so clearly."
                )
            
            # Prepare the request for Claude model
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Context:\\n{context}\\n\\nQuestion: {query}"
                    }
                ],
                "system": system_prompt
            }
            
            # Call the Bedrock model
            response = self.bedrock_runtime.invoke_model(
                modelId=os.getenv("AWS_BEDROCK_MODEL_ID"),
                body=json.dumps(request_body)
            )
            
            # Parse the response
            response_body = json.loads(response["body"].read().decode())
            return response_body["content"][0]["text"]
            
        except Exception as e:
            logger.error(f"Error querying Knowledge Base with LLM: {str(e)}")
            raise


def evaluate_kb_against_criteria(
    kb_id: str,
    retriever_id: str,
    project_name: str,
    gate_review: CriterionGate,
    storage_handler: PostgresStorageHandler,
    criteria_csv_list: List[str]
) -> None:
    """
    Evaluate an AWS Bedrock Knowledge Base against criteria
    
    Args:
        kb_id: AWS Bedrock Knowledge Base ID
        retriever_id: Knowledge Base retriever ID
        project_name: Name to use for the project in the database
        gate_review: Gate review type (e.g., GATE_2, GATE_3)
        storage_handler: Database storage handler
        criteria_csv_list: List of CSV files containing criteria
    """
    # Create KB client
    kb = BedrockKnowledgeBase(kb_id, retriever_id)
    
    # Ingest criteria from CSVs
    ingest_criteria_from_local_dir(gate_filepaths=criteria_csv_list, storage_handler=storage_handler)
    logger.info("Criteria ingested")
    
    # Create project in database
    project = ProjectCreate(
        name=project_name,
        storage_kind="bedrock_kb",
        external_id=kb_id
    )
    project = storage_handler.write_item(project)
    logger.info(f"Created project: {project.name}")
    
    # Get criteria for gate
    filter = {"gate": gate_review}
    criteria = storage_handler.get_item_by_attribute(filter)
    logger.info(f"{len(criteria)} criteria loaded")
    
    # Create custom MainEvaluator that uses KB for retrieval
    class KBMainEvaluator(MainEvaluator):
        def semantic_search(self, query: str, k: int, filters: dict):
            # Override to use KB instead of vector store
            documents = kb.retrieve(query=query, max_results=k)
            
            # Format into expected prompt structure
            prompt = "Document extracts relevant to the query:\n\n"
            for i, doc in enumerate(documents):
                prompt += f"Document {i+1}: {doc['metadata']['document_id']}\n"
                prompt += f"Content: {doc['content']}\n\n"
            
            return prompt, documents
    
    # Initialize evaluator
    evaluator = KBMainEvaluator(
        project=project,
        vector_store=None,  # Not used with KB
        llm=boto3.client(service_name="bedrock-runtime", region_name=os.getenv("AWS_REGION")),
        storage_handler=storage_handler
    )
    
    # Evaluate criteria
    results = evaluator.evaluate_questions(criteria=criteria, save=True)
    logger.info(f"Evaluated {len(results)} criteria against Knowledge Base")
    
    # Generate summary and save to project
    summary = evaluator.generate_summary([(c.question, r.full_text) for c, r in zip(criteria, results)])
    project.results_summary = summary
    storage_handler.update_item(project)
    logger.info("Evaluation complete")


if __name__ == "__main__":
    # These are your settings
    kb_id = os.getenv("AWS_BEDROCK_KB_ID", "")  # AWS Bedrock Knowledge Base ID
    retriever_id = os.getenv("AWS_BEDROCK_RETRIEVER_ID", "")  # AWS Bedrock Retriever ID
    project_name = "bedrock_kb_project"  # Name to use in Scout
    
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
        retriever_id=retriever_id,
        project_name=project_name,
        gate_review=gate_review,
        storage_handler=storage_handler,
        criteria_csv_list=criteria_csv_list
    )