import os
from functools import lru_cache

from application.use_cases import SubmitCapturaUseCase
from infrastructure.dynamo_repository import DynamoCapturaRepository
from infrastructure.s3_storage import S3StorageService

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "blick-capturas-tcc")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "blick-table")


@lru_cache
def get_s3_storage() -> S3StorageService:
    return S3StorageService(bucket_name=S3_BUCKET_NAME, region=AWS_REGION)


@lru_cache
def get_dynamo_repository() -> DynamoCapturaRepository:
    return DynamoCapturaRepository(table_name=DYNAMODB_TABLE_NAME, region=AWS_REGION)


def get_submit_captura_use_case() -> SubmitCapturaUseCase:
    return SubmitCapturaUseCase(
        storage=get_s3_storage(),
        repository=get_dynamo_repository(),
        s3_bucket=S3_BUCKET_NAME,
    )
