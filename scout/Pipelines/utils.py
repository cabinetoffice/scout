import os
from pathlib import Path
import boto3

from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockEmbeddings


def get_or_create_vector_store(vector_store_directory: Path):
    # Create Bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION")
    )
    
    # Use AWS Bedrock embeddings
    embedding_function = BedrockEmbeddings(
        client=bedrock_client,
        model_id=os.getenv("AWS_BEDROCK_EMBEDDING_MODEL_ID")
    )

    # Check if an existing vector store exists and handle dimension mismatch
    if os.path.exists(vector_store_directory) and os.path.isdir(vector_store_directory):
        import shutil
        import logging
        
        logger = logging.getLogger(__name__)
        logger.warning(
            "Existing vector store found. Recreating with new embedding model to avoid dimension mismatch. "
            "This will delete your existing embeddings!"
        )
        
        # Remove the existing vector store directory
        shutil.rmtree(vector_store_directory)
        
        # Create directory again
        os.makedirs(vector_store_directory, exist_ok=True)

    # Create new vector store with Bedrock embeddings
    vector_store = Chroma(
        embedding_function=embedding_function,
        persist_directory=str(vector_store_directory),
        collection_metadata={
            "hnsw:M": 2048,
            "hnsw:search_ef": 20,
        },  # included to avoid M too small error on retrival
    )
    return vector_store
