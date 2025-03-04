# utils.py
import json
import logging.config
import os
import pathlib
from typing import Dict
from sqlalchemy import create_engine, text
from typing import List, Tuple
import dotenv
from langchain_community.llms.sagemaker_endpoint import LLMContentHandler
from langchain_community.vectorstores import Chroma
from langchain_aws import BedrockChat, BedrockEmbeddings
from botocore.exceptions import ClientError
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from scout.utils.storage.filesystem import S3StorageHandler
from scout.utils.storage.sqlite_storage_handler import SQLiteStorageHandler


def setup_logging(persistency_folder_path):
    log_file_path = os.path.join(persistency_folder_path, "app.log")
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "level": "INFO",
                "formatter": "standard",
                "class": "logging.FileHandler",
                "filename": str(log_file_path),
                "mode": "a",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["default", "file"],
                "level": "INFO",
                "propagate": True,
            },
            "scout": {
                "handlers": ["default", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


logger = logging.getLogger(__name__)


def api_call_with_retry(max_attempts=10, min_wait=4, max_wait=10):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ClientError,)),
        before_sleep=lambda retry_state: logger.info(f"Retrying in {retry_state.next_action.sleep} seconds..."),
    )


class ContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps({"inputs": prompt, "parameters": model_kwargs})
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json[0]["generated_text"]


class SessionState:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SessionState, cls).__new__(cls)
            cls._instance.state = {}
        return cls._instance

    def set(self, key, value):
        self.state[key] = value

    def get(self, key, default=None):
        return self.state.get(key, default)


def init_session_state(
    persistency_folder_path: str = None,
    deploy_mode: bool = False,
) -> dict:
    """Initialise the session state for the app"""

    session_state = SessionState()

    # Load environment variables
    dotenv.load_dotenv(".env")
    ENV = dotenv.dotenv_values(".env")

    if "persistency_folder_path" not in dir(session_state) and not deploy_mode:
        if persistency_folder_path is not None:
            session_state.persistency_folder_path = pathlib.Path(".data/db" + "_" + persistency_folder_path)
        else:
            session_state.persistency_folder_path = pathlib.Path(".data/db")
        if not os.path.exists(session_state.persistency_folder_path):
            os.makedirs(session_state.persistency_folder_path)

    setup_logging(
        persistency_folder_path=session_state.persistency_folder_path
    )  # Set up logging as part of initialization
    logger.info("Initializing session state")

    if "storage_handler" not in dir(session_state):
        session_state.storage_handler = SQLiteStorageHandler(session_state.persistency_folder_path / "main.db")
        logger.info("SQLite storage handler initialized")

    if "s3_storage_handler" not in dir(session_state):
        s3_url = os.environ.get("S3_URL", None)
        if not s3_url:
            session_state.s3_storage_handler = S3StorageHandler(
                bucket_name=os.environ.get("BUCKET_NAME"),
                region_name=os.environ.get("S3_REGION"),
            )
            logger.info("AWS S3 storage handler initialized")
        else:
            logger.info("Connecting to minio...")
            session_state.s3_storage_handler = S3StorageHandler(
                os.environ.get("BUCKET_NAME"),
                endpoint_url=s3_url,
            )
            logger.info("Minio S3 storage handler initialized")

    if "llm" not in dir(session_state) and not deploy_mode:
        import boto3
        from langchain_aws import BedrockChat

        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=os.getenv("AWS_REGION")
        )
        
        session_state.llm = BedrockChat(
            client=bedrock_client,
            model_id=os.getenv("AWS_BEDROCK_MODEL_ID")
        )
        logger.info("AWS Bedrock LLM initialized")

    if "llm_summarizer" not in dir(session_state) and not deploy_mode:
        import boto3
        from langchain_aws import BedrockChat

        if "bedrock_client" not in locals():
            bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_REGION")
            )
        
        session_state.llm_summarizer = BedrockChat(
            client=bedrock_client,
            model_id=os.getenv("AWS_BEDROCK_MODEL_ID")
        )
        logger.info("AWS Bedrock summarizer initialized")

    if "embedding_function" not in dir(session_state) and not deploy_mode:
        try:
            from langchain_aws import BedrockEmbeddings
            
            # Use AWS Bedrock for embeddings
            if "bedrock_client" not in locals():
                import boto3
                bedrock_client = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=os.getenv("AWS_REGION")
                )
            
            session_state.embedding_function = BedrockEmbeddings(
                client=bedrock_client,
                model_id=os.getenv("AWS_BEDROCK_EMBEDDING_MODEL_ID")
            )
            logger.info("AWS Bedrock embeddings initialized")
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}")
            raise

    if "topic_embedding_function" not in dir(session_state) and not deploy_mode:
        try:
            from langchain_aws import BedrockEmbeddings
            
            # Use AWS Bedrock for topic embeddings
            if "bedrock_client" not in locals():
                import boto3
                bedrock_client = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=os.getenv("AWS_REGION")
                )
            
            session_state.topic_embedding_function = BedrockEmbeddings(
                client=bedrock_client,
                model_id=os.getenv("AWS_BEDROCK_EMBEDDING_MODEL_ID")
            )
            logger.info("AWS Bedrock topic embeddings initialized")
        except Exception as e:
            logger.error(f"Error initializing embeddings for topics: {e}")
            raise

    if "vector_store" not in dir(session_state) and not deploy_mode:
        persist_directory = os.path.join(session_state.persistency_folder_path, "VectorStore")

        # Check if an existing vector store exists and handle dimension mismatch
        if os.path.exists(persist_directory) and os.path.isdir(persist_directory):
            import shutil
            
            logger.warning(
                "Existing vector store found. Recreating with new embedding model to avoid dimension mismatch. "
                "This will delete your existing embeddings!"
            )
            
            # Remove the existing vector store directory
            shutil.rmtree(persist_directory)
        
        # Create directory
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)

        session_state.vector_store = Chroma(
            embedding_function=session_state.embedding_function,
            persist_directory=persist_directory,
        )
        logger.info("Vector store initialized")

    logger.info("Session state initialization completed")

    return ENV, session_state


def check_table_rows(connection_string: str, expected_counts: Dict[str, int]) -> List[Tuple[str, bool, int, int]]:
    """
    Check if tables have the expected number of rows within a threshold.

    Args:
        connection_string: Database connection string
        expected_counts: Dictionary mapping table names to their expected row counts

    Returns:
        List of tuples: (table_name, passed_check, actual_count, expected_count)
    """
    engine = create_engine(connection_string)
    results = []

    with engine.connect() as conn:
        for table_name, expected_count in expected_counts.items():
            try:
                # Get actual row count
                actual_count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

                # Check if count is correct
                passed = actual_count == expected_count

                results.append((table_name, passed, actual_count, expected_count))

                # Print result
                status = "PASSED" if passed else "FAILED"
                print(f"{table_name}: {status} (Expected: {expected_count}, Actual: {actual_count})")

            except Exception as e:
                print(f"Error checking {table_name}: {str(e)}")
                results.append((table_name, False, -1, expected_count))

    # Print summary
    passed_count = sum(1 for r in results if r[1])
    print(f"\nTotal passed: {passed_count}/{len(results)} checks")

    return results
