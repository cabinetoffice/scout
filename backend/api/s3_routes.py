import logging
import typing
from uuid import UUID

import boto3
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend.api.routes import get_current_user
from scout.DataIngest.models.schemas import User as PyUser, File as PyFile, FileFilter
from scout.utils.storage import postgres_interface as interface

logger = logging.getLogger(__name__)

router = APIRouter()
if typing.TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


def get_s3_client() -> "S3Client":
    """
    Creates and returns an S3 client.
    """
    try:
        s3_client = boto3.client('s3')
        return s3_client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating S3 client: {e}")


@router.get("/get_file/{uuid}", response_class=StreamingResponse)
def get_file(
    uuid: UUID,
    current_user: PyUser = Depends(get_current_user),
    s3_client: "S3Client" = Depends(get_s3_client)
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

        s3_obj = s3_client.get_object(Bucket=file.s3_bucket, Key=file.s3_key)

        return StreamingResponse(
            s3_obj["Body"].iter_chunks(chunk_size=1024 * 1024),
            media_type=file_type,
            headers={
                "Content-Disposition": f"attachment; filename={file.s3_key.split('/')[-1]}",
                "X-File-Type": file_type,
            }
        )

    except Exception as e:
        logger.exception("An error occurred while retrieving the file")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving the file: {str(e)}",
        )


@router.get("/get_file_by_key/{key}", response_class=StreamingResponse)
def get_file_by_key(
    key: str,
    current_user: PyUser = Depends(get_current_user),
    s3_client: "S3Client" = Depends(get_s3_client)
):
    try:
        # Find the file in the database by its S3 key
        file = interface.filter_items(FileFilter(s3_key=key), current_user)
        if not file or len(file) == 0:
            raise HTTPException(status_code=404, detail="File not found")

        file = file[0]  # Get the first matching file
        file_extension = file.s3_key.split(".")[-1].lower()

        # Determine the file type
        if file_extension == "pdf":
            file_type = "application/pdf"
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        s3_obj = s3_client.get_object(Bucket=file.s3_bucket, Key=file.s3_key)

        return StreamingResponse(
            s3_obj["Body"].iter_chunks(chunk_size=1024 * 1024),
            media_type=file_type,
            headers={
                "Content-Disposition": f"attachment; filename={file.s3_key.split('/')[-1]}",
                "X-File-Type": file_type,
            }
        )

    except Exception as e:
        logger.exception("An error occurred while retrieving the file by key")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving the file: {str(e)}",
        )
