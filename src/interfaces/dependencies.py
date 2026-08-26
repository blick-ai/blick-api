import os
from functools import lru_cache

from fastapi.security import HTTPBearer

from application.use_cases import (
    ClassifyCapturaUseCase,
    ClassifyPendentesUseCase,
    DeletarCapturaUseCase,
    BackfillOrigemUseCase,
    GerarThumbnailsUseCase,
    GetCapturaUseCase,
    ListCapturasUseCase,
    ListClientesUseCase,
    ReclassificarTodasUseCase,
    SubmitCapturaSimplesUseCase,
    SubmitCapturaUseCase,
)
from infrastructure.cognito_auth import CognitoAuthService
from infrastructure.dynamo_repository import DynamoCapturaRepository
from infrastructure.s3_storage import S3StorageService
from infrastructure.sagemaker_classifier import SageMakerClassificationService

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "blick-capturas-tcc")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "blick-table")
SAGEMAKER_ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME", "blick-classificador")

security = HTTPBearer()


@lru_cache
def get_s3_storage() -> S3StorageService:
    return S3StorageService(bucket_name=S3_BUCKET_NAME, region=AWS_REGION)


@lru_cache
def get_dynamo_repository() -> DynamoCapturaRepository:
    return DynamoCapturaRepository(table_name=DYNAMODB_TABLE_NAME, region=AWS_REGION)


@lru_cache
def get_auth_service() -> CognitoAuthService:
    return CognitoAuthService()


@lru_cache
def get_classification_service() -> SageMakerClassificationService:
    return SageMakerClassificationService(endpoint_name=SAGEMAKER_ENDPOINT_NAME, region=AWS_REGION)


def get_submit_captura_use_case() -> SubmitCapturaUseCase:
    return SubmitCapturaUseCase(
        storage=get_s3_storage(),
        repository=get_dynamo_repository(),
        s3_bucket=S3_BUCKET_NAME,
    )


def get_submit_captura_simples_use_case() -> SubmitCapturaSimplesUseCase:
    return SubmitCapturaSimplesUseCase(
        storage=get_s3_storage(),
        repository=get_dynamo_repository(),
        s3_bucket=S3_BUCKET_NAME,
    )


def get_classify_captura_use_case() -> ClassifyCapturaUseCase:
    return ClassifyCapturaUseCase(
        repository=get_dynamo_repository(),
        storage=get_s3_storage(),
        classifier=get_classification_service(),
    )


def get_classify_pendentes_use_case() -> ClassifyPendentesUseCase:
    return ClassifyPendentesUseCase(
        repository=get_dynamo_repository(),
        classify_use_case=get_classify_captura_use_case(),
    )


def get_reclassificar_todas_use_case() -> ReclassificarTodasUseCase:
    return ReclassificarTodasUseCase(
        repository=get_dynamo_repository(),
        classify_use_case=get_classify_captura_use_case(),
    )


def get_gerar_thumbnails_use_case() -> GerarThumbnailsUseCase:
    return GerarThumbnailsUseCase(
        repository=get_dynamo_repository(),
        storage=get_s3_storage(),
    )


def get_backfill_origem_use_case() -> BackfillOrigemUseCase:
    return BackfillOrigemUseCase(repository=get_dynamo_repository())


def get_list_capturas_use_case() -> ListCapturasUseCase:
    return ListCapturasUseCase(repository=get_dynamo_repository(), storage=get_s3_storage())


def get_captura_use_case() -> GetCapturaUseCase:
    return GetCapturaUseCase(repository=get_dynamo_repository(), storage=get_s3_storage())


def get_deletar_captura_use_case() -> DeletarCapturaUseCase:
    return DeletarCapturaUseCase(repository=get_dynamo_repository(), storage=get_s3_storage())


def get_list_clientes_use_case() -> ListClientesUseCase:
    return ListClientesUseCase(repository=get_dynamo_repository())
