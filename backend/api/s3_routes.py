import boto3
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from backend.api.routes import get_current_user
from scout.DataIngest.models.schemas import User as PyUser

router = APIRouter()

def get_s3_client():
    """
    Creates and returns an S3 client.
    """
    try:
        s3_client = boto3.client('s3')
        return s3_client
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating S3 client: {e}")


@router.get("/list_buckets/", response_model=List[str])
async def list_s3_buckets(
    s3_client: boto3.client = Depends(get_s3_client)
):
    """
    Lists all S3 buckets in the account.

    Args:
        s3_client: An S3 client instance.
        current_user: The current user (for authentication/authorization).

    Returns:
        A list of bucket names.

    Raises:
        HTTPException: If there's an error listing buckets.
    """
    try:
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        return buckets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing S3 buckets: {e}")
