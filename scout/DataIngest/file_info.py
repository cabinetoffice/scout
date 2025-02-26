import os
import json

import boto3
import instructor
from instructor.exceptions import InstructorRetryException
from pydantic.json import pydantic_encoder

from scout.DataIngest.models.schemas import ChunkCreate, File, FileInfo, FileUpdate
from scout.DataIngest.prompts import FILE_INFO_EXTRACTOR_SYSTEM_PROMPT
from scout.utils.storage.storage_handler import BaseStorageHandler

from scout.utils.utils import logger


def get_text_from_chunks(chunks: list[ChunkCreate], num_chunks: int):
    chunks = [chunk.text for chunk in chunks[:num_chunks]]
    text = " ".join(chunks)
    return text


def get_llm_file_info(project_name: str, file_name: str, text: str) -> FileInfo:
    """
    For a given file and text, get LLM generated metadata on file (FileInfo) e.g. name, summary.
    If LLM generated info fails - return blank FileInfo.
    """
    # Create bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION")
    )
    
    # Create prompt that will be used to generate file info
    sys_prompt = FILE_INFO_EXTRACTOR_SYSTEM_PROMPT.format(project_name=project_name, file_name=file_name)
    
    # Extract structured metadata for file from natural language using Bedrock
    try:
        # Create the messages for Claude/Anthropic model format
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": text}
        ]
        
        # Create a prompt with instructions to output JSON for FileInfo schema
        schema_instructions = """
        Return the output as valid JSON with the following structure:
        {
            "clean_name": "string",
            "source": "Government | Supplier | Other",
            "summary": "string",
            "published_date": "YYYY-MM-DD string or null"
        }
        """
        
        # Add instruction for response format
        messages.append({"role": "user", "content": schema_instructions})
        
        # Make the API call to Bedrock with Claude
        response = bedrock_client.invoke_model(
            modelId=os.getenv("AWS_BEDROCK_MODEL_ID"),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": messages
            })
        )
        
        # Parse the response
        response_body = json.loads(response["body"].read().decode())
        output_content = response_body["content"][0]["text"]
        
        # Extract JSON from the response
        import re
        json_match = re.search(r'```json\n(.*?)\n```', output_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = output_content
        
        # Clean up any non-JSON content
        json_str = json_str.strip()
        if json_str.startswith('```') and json_str.endswith('```'):
            json_str = json_str[3:-3].strip()
        
        # Parse JSON into FileInfo object
        file_info_dict = json.loads(json_str)
        file_info = FileInfo(**file_info_dict)
        
    except Exception as e:
        # Assumption that blank info is fine if we can't generate with LLM
        file_info = FileInfo()
        logger.error(f"{e} unable to get LLM generated file info for {file_name}, proceeding without...")

    logger.info("File info generated")
    return file_info


def get_file_update(file: File, file_info: FileInfo) -> FileUpdate:
    # Pre-populate a FileUpdate object with the details from File object
    file_update = FileUpdate(
        type=file.type,
        name=file.name,
        s3_bucket=getattr(file, "s3_bucket", None),
        s3_key=getattr(file, "s3_key", None),
        storage_kind=getattr(file, "storage_kind", "local"),
        project=getattr(file, "project", None),
        chunks=getattr(file, "chunks", []),
        id=file.id,
    )
    # Add the updated file info to update file - there is a chance that
    file_update.clean_name = file_info.clean_name
    file_update.source = file_info.source.value if file_info.source else None
    file_update.summary = file_info.summary
    file_update.published_date = file_info.published_date
    return file_update


def add_llm_generated_file_info(
    project_name: str, file: File, chunks_from_file: list[ChunkCreate], storage_handler: BaseStorageHandler
) -> File:
    text = get_text_from_chunks(chunks=chunks_from_file, num_chunks=20)
    llm_generated_file_info = get_llm_file_info(project_name=project_name, file_name=file.name, text=text)
    file_update = get_file_update(file=file, file_info=llm_generated_file_info)
    updated_file = storage_handler.update_item(file_update)
    return updated_file
