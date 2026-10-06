import json

import boto3

from domain.agregacao import agregar_por_planta
from domain.entities import ClassificacaoResultado
from domain.ports import IClassificationService


class SageMakerClassificationService(IClassificationService):
    """
    Adaptador que chama o endpoint do SageMaker hospedando o pipeline
    treinado no repositorio blick-model (ver sagemaker/inference.py la —
    o formato de resposta abaixo espelha exatamente o que aquele
    predict_fn devolve: segmentacao milho/nao-milho -> isolamento por
    planta -> classificacao saudavel/nao_saudavel por planta).
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

        status_geral = corpo["status_geral"]
        confianca_status_geral = corpo["confianca_status_geral"]
        analise_por_planta = corpo.get("analise_por_planta", [])

        # o status da foto e decidido aqui, a partir do detalhe por planta
        # (regra em domain/agregacao.py), e nao mais pelo que o SageMaker
        # agregou. "nao_milho" continua vindo do endpoint.
        if status_geral in ("saudavel", "nao_saudavel") and analise_por_planta:
            agregado = agregar_por_planta(analise_por_planta)
            if agregado is not None:
                status_geral, confianca_status_geral = agregado

        return ClassificacaoResultado(
            status_geral=status_geral,
            confianca_status_geral=confianca_status_geral,
            # chave corrigida: o inference.py devolve "probabilidades"
            # (nao "probabilidades_status_geral" — essa leitura estava
            # errada e sempre caia no fallback {} antes dessa correcao)
            probabilidades=corpo.get("probabilidades", {}),
            subtipo=corpo.get("subtipo"),
            confianca_subtipo=corpo.get("confianca_subtipo"),
            analise_por_planta=analise_por_planta,
        )
