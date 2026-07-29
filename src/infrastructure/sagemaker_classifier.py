import json

import boto3

from domain.entities import ClassificacaoResultado
from domain.ports import IClassificationService


class SageMakerClassificationService(IClassificationService):
    """
    Adaptador que chama o endpoint do SageMaker hospedando o modelo
    treinado no repositorio blick-model (ver sagemaker/inference.py la —
    o formato de resposta abaixo espelha exatamente o que aquele
    predict_fn devolve).
    """

    def __init__(self, endpoint_name: str, region: str):
        self._endpoint_name = endpoint_name
        self._client = boto3.client("sagemaker-runtime", region_name=region)

    def classify(self, image_bytes: bytes) -> ClassificacaoResultado:
        response = self._client.invoke_endpoint(
            EndpointName=self._endpoint_name,
            ContentType="application/x-image",
            Accept="application/json",
            Body=image_bytes,
        )
        corpo = json.loads(response["Body"].read())

        return ClassificacaoResultado(
            status_geral=corpo["status_geral"],
            confianca_status_geral=corpo["confianca_status_geral"],
            probabilidades=corpo.get("probabilidades_status_geral", {}),
            subtipo=corpo.get("subtipo"),
            confianca_subtipo=corpo.get("confianca_subtipo"),
        )
