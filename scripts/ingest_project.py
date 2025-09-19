#!/usr/bin/env python3
import os
import pathlib
import time

import botocore.exceptions
import boto3
import dotenv
import sys

import scout.Pipelines.utils
import scout.Pipelines.ingest_project_data

ROOT_DIR = pathlib.Path(__file__).parent.parent.resolve()

REQUIRED_ENV = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "AWS_BEDROCK_MODEL_ID",
    "AWS_BEDROCK_EMBEDDING_MODEL_ID",
    "AWS_BEDROCK_KB_ID",
    "BUCKET_NAME",
    "AWS_ENDPOINT_URL_S3",
    "LIBREOFFICE_SERVICE_URL",
    "AWS_REGION"
]

bedrock_agent = boto3.client(
    service_name="bedrock-agent",
    region_name=os.getenv("AWS_REGION")
)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <PROJECT_NAME>")
        sys.exit(1)

    os.chdir(ROOT_DIR)
    project_name = sys.argv[1]
    project_path = ROOT_DIR / ".data" / project_name

    if not project_path.is_dir():
        print(f"{project_path} does not exist or is not a directory")

    dotenv.load_dotenv()

    env_not_set = []
    for env in REQUIRED_ENV:
        if env not in os.environ:
            env_not_set.append(env)

    if env_not_set:
        print(
            "Required environment variables not set:",
            ", ".join(env_not_set)
        )
        sys.exit(2)

    store = scout.Pipelines.utils.get_or_create_vector_store(
        project_path / "VectorStore"
    )
    scout.Pipelines.ingest_project_data.ingest_project_files(
        project_name,
        store
    )

    knowledge_base_id = os.environ["AWS_BEDROCK_KB_ID"]
    response = bedrock_agent.list_data_sources(
        knowledgeBaseId=knowledge_base_id,
        maxResults=1
    )
    data_source_id = response["dataSourceSummaries"][0]["dataSourceId"]

    ingestion_job = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=knowledge_base_id,
        dataSourceId=data_source_id
    )

    print(f"Ingestion job started successfully!")
    ingestion_job_id = ingestion_job['ingestionJob']['ingestionJobId']
    print(f"Job ID: {ingestion_job_id}")
    print(f"Status: {ingestion_job['ingestionJob']['status']}")

    while True:
        try:
            response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=knowledge_base_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id
            )

            job = response['ingestionJob']
            status = job['status']

            print(f"Job Status: {status}")

            if status in ['COMPLETE', 'FAILED']:
                print(f"Job finished with status: {status}")
                if 'failureReasons' in job:
                    print(f"Failure reasons: {job['failureReasons']}")
                break
            elif status == 'IN_PROGRESS':
                print("Job is still running...")
                time.sleep(5)  # Wait 30 seconds before checking again

        except botocore.exceptions.ClientError as e:
            print(f"Error checking job status: {e}")
            break
