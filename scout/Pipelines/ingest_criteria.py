import csv
import os
from typing import List

from scout.DataIngest.models.schemas import CriterionCreate as Criterion
from scout.DataIngest.models.schemas import Chunk, ChunkCreate, CriterionCreate, CriterionGate, FileCreate, ProjectCreate
from scout.utils.storage.storage_handler import BaseStorageHandler
from scout.utils.utils import logger


import boto3
from botocore.config import Config
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException

from scout.utils.storage.postgres_storage_handler import PostgresStorageHandler


header_mapping = {
    "Category": "category",
    "Question": "question",
    "Evidence": "evidence",
    "Gate": "gate",
}

def load_criteria_csv_to_storage(
    storage_handler: BaseStorageHandler,
    file_path: str,
) -> int:
    """
    Uploads criteria from a single csv to the database.

    Args:
        folder_path (str): Path to the folder containing criteria CSVs.
            CSV files should be named after their gate and have the headings:
            "Category", "Question", "Evidence", "Gate".
        Storage Handler: Session state object.

    Returns:
        int: Number of records uploaded.

    Raises:
        FileNotFoundError: If the folder_path doesn't exist.
        ValueError: If a CSV file is empty or has incorrect headers.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The folder '{file_path}' does not exist.")


    records_uploaded = 0

    try:
        with open(file_path, mode="r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            if not reader.fieldnames:
                raise ValueError(f"The CSV file '{file_path}' is empty or has no headers.")
            for row in reader:
                mapped_row = {header_mapping.get(k, k): v.strip() for k, v in row.items()}
                try:
                    model_instance = Criterion(**mapped_row)
                    storage_handler.write_item(model_instance)
                    records_uploaded += 1
                except Exception as e:
                    logger.error(f"Error processing row in '{file_path}': {e}")
                    continue

    except Exception as e:
        logger.error(f"Error reading from file '{file_path}': {e}")

    logger.info(f"Successfully uploaded {records_uploaded} criteria to db.")
    return records_uploaded


def ingest_criteria_from_local_dir(
    gate_filepaths: List[str],
    storage_handler: BaseStorageHandler,
) -> None:
    """
    Ingest criteria from CSV files into the database.
    """
    [
        load_criteria_csv_to_storage(storage_handler=storage_handler, file_path=gate_filepath)
        for gate_filepath in gate_filepaths
    ]
    logger.info("Successfully ingested criteria")


def ingest_criteria_from_s3(
    gate_filepaths: List[str],
    storage_handler: PostgresStorageHandler,
    bucket_name: str = os.getenv("BUCKET_NAME"),
    region_name: str = None,
) -> None:
    """
    Ingests criteria from CSV files stored in an S3 bucket.

    Args:
        gate_filepaths: List of S3 keys (file paths) to CSV files.
        storage_handler: Database storage handler.
        bucket_name: Name of the S3 bucket.
        region_name: AWS region name (defaults to session region).
    """
    session = boto3.session.Session()
    region = os.environ.get("AWS_REGION", "eu-west-2")
    endpoint_url = os.environ.get("S3_URL")
    s3_client = boto3.client(
        "s3",
        region_name=region,
    )
    for file_path in gate_filepaths:
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
            csv_content = response["Body"].read().decode("utf-8")
            reader = csv.DictReader(csv_content.splitlines())

            records_uploaded = 0
            
            if not reader.fieldnames:
                raise ValueError(f"The CSV file '{file_path}' is empty or has no headers.")
            for row in reader:
                mapped_row = {header_mapping.get(k, k): v.strip() for k, v in row.items()}
                try:
                    model_instance = Criterion(**mapped_row)
                    storage_handler.write_item(model_instance)
                    records_uploaded += 1
                except Exception as e:
                    logger.error(f"Error processing row in '{file_path}': {e}")
                    continue

            logger.info(f"Successfully uploaded {records_uploaded} criteria to db.")

        except NoCredentialsError:
            logger.error("AWS credentials not available.")
            raise HTTPException(
                status_code=500, detail="AWS credentials not available."
            )
        except s3_client.exceptions.NoSuchKey:
            logger.error(f"File not found in S3: {bucket_name}/{file_path}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found in S3: {bucket_name}/{file_path}",
            )
        except Exception as e:
            logger.error(f"Error reading criteria from S3: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error reading criteria from S3: {e}"
            )
    logger.info("Criteria ingested from S3")
