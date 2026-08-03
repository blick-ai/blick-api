import base64
import uuid
from datetime import datetime

from application.dtos import (
    CapturaDetalheDTO,
    CapturaInputDTO,
    CapturaOutputDTO,
    CapturaResumoDTO,
    ListCapturasOutputDTO,
    ListClientesOutputDTO,
)
from domain.entities import Captura, Coordenadas, JetsonNanoInfo, StatusEntry
from domain.ports import ICapturaRepository, IClassificationService, IStorageService

MOCK_PLANTACAO_ID = "plantacao-mock-001"
MOCK_CARRINHO_ID = "carrinho-mock-001"


class SubmitCapturaUseCase:
    def __init__(
        self,
        storage: IStorageService,
        repository: ICapturaRepository,
        s3_bucket: str,
    ):
        self._storage = storage
        self._repository = repository
        self._s3_bucket = s3_bucket

    def execute(self, dto: CapturaInputDTO) -> CapturaOutputDTO:
        image_bytes = base64.b64decode(dto.imagem_base64)

        now = datetime.utcnow()
        timestamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        short_uuid = uuid.uuid4().hex[:8]
        captura_id = f"{now.strftime('%Y%m%d%H%M%S')}-{short_uuid}"

        date = datetime.strptime(dto.dia_mes_ano, "%d/%m/%Y")
        dia, mes, ano = date.strftime("%d"), date.strftime("%m"), date.strftime("%Y")
        s3_key = f"{dto.cliente_id}/{ano}/{mes}/{dia}/{captura_id}.jpg"

        self._storage.upload_image(s3_key, image_bytes)

        captura = Captura(
            captura_id=captura_id,
            cliente_id=dto.cliente_id,
            plantacao_id=MOCK_PLANTACAO_ID,
            carrinho_id=MOCK_CARRINHO_ID,
            timestamp=timestamp,
            coordenadas=Coordenadas(
                latitude=dto.latitude,
                longitude=dto.longitude,
            ),
            s3_bucket=self._s3_bucket,
            s3_key=s3_key,
            jetson_nano=JetsonNanoInfo(
                planta_detectada=True,
                confianca=dto.confianca_borda if dto.confianca_borda is not None else 0.0,
                # antes fixo em "ia-blick-v2" mesmo quando o worker de envio
                # do Klar ja manda a versao real do modelo de borda (ver
                # capturar_zed.py — plants_v1.tflite, nao ia-blick-v2).
                # Agora usa o que vier do cliente, com fallback pra nao quebrar
                # chamadas antigas que ainda nao mandam esse campo.
                modelo_versao=dto.modelo_versao_borda or "desconhecida",
            ),
            status="PENDENTE",
            status_history=[StatusEntry(status="PENDENTE", timestamp=timestamp)],
        )

        self._repository.save(captura)

        return CapturaOutputDTO(
            sucesso=True,
            captura_id=captura_id,
            s3_key=s3_key,
        )


class ClassifyCapturaUseCase:
    """
    Baixa a imagem da captura, manda pro modelo de nuvem (via
    IClassificationService) e atualiza a captura com o resultado.

    Pensado pra ser chamado de forma assincrona (worker separado, nao no
    mesmo request de SubmitCapturaUseCase) — ver conversa sobre rajada de
    capturas quando o Klar volta a ter Wi-Fi, que motivou esse desenho.
    """

    def __init__(
        self,
        repository: ICapturaRepository,
        storage: IStorageService,
        classifier: IClassificationService,
    ):
        self._repository = repository
        self._storage = storage
        self._classifier = classifier

    def execute(self, plantacao_id: str, timestamp: str, captura_id: str) -> Captura:
        captura = self._repository.get(plantacao_id, timestamp, captura_id)
        if captura is None:
            raise ValueError(f"Captura não encontrada: {captura_id}")

        agora = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            image_bytes = self._storage.download_image(captura.s3_key)
            resultado = self._classifier.classify(image_bytes)
        except Exception as e:
            captura.status = "ERRO"
            captura.erro_detalhes = str(e)
            captura.status_history.append(StatusEntry(status="ERRO", timestamp=agora))
            self._repository.update(captura)
            raise

        captura.ia_nuvem = resultado.to_dict()
        captura.status = "CLASSIFICADO"
        # limpa erro de uma tentativa anterior mal sucedida, se houver —
        # sem isso, reclassificar uma captura que falhou antes deixava a
        # mensagem de erro velha "grudada" mesmo com sucesso agora
        captura.erro_detalhes = None
        captura.status_history.append(StatusEntry(status="CLASSIFICADO", timestamp=agora))

        # alerta so faz sentido se nao for planta saudavel nem "nao_milho"
        # (nao_milho e ruido de captura, nao problema na lavoura)
        if resultado.status_geral in ("praga", "doenca"):
            captura.alerta_emitido = True
            captura.alerta_emitido_em = agora

        self._repository.update(captura)
        return captura


class ClassifyPendentesUseCase:
    """Processa em lote as capturas que ainda estao com status PENDENTE."""

    def __init__(self, repository: ICapturaRepository, classify_use_case: ClassifyCapturaUseCase):
        self._repository = repository
        self._classify_use_case = classify_use_case

    def execute(self, limite: int = 50) -> dict:
        pendentes = self._repository.list_by_status("PENDENTE", limit=limite)
        processadas, erros = 0, 0

        for captura in pendentes:
            try:
                self._classify_use_case.execute(
                    captura.plantacao_id, captura.timestamp, captura.captura_id
                )
                processadas += 1
            except Exception:
                erros += 1

        return {"total": len(pendentes), "processadas": processadas, "erros": erros}


class ListClientesUseCase:
    def __init__(self, repository: ICapturaRepository):
        self._repository = repository

    def execute(self) -> ListClientesOutputDTO:
        cliente_ids = self._repository.list_cliente_ids()
        return ListClientesOutputDTO(cliente_ids=cliente_ids)


def _resumo_de(captura: Captura) -> CapturaResumoDTO:
    ia = captura.ia_nuvem or {}
    return CapturaResumoDTO(
        captura_id=captura.captura_id,
        timestamp=captura.timestamp,
        status=captura.status,
        status_geral=ia.get("status_geral"),
        confianca_status_geral=(
            float(ia["confianca_status_geral"]) if ia.get("confianca_status_geral") is not None else None
        ),
        latitude=captura.coordenadas.latitude,
        longitude=captura.coordenadas.longitude,
        alerta_emitido=captura.alerta_emitido,
    )


class ListCapturasUseCase:
    """
    GET geral — lista enxuta de capturas de uma plantacao, mais recentes
    primeiro por padrao. Suporta filtro por status_geral (saudavel/praga/
    doenca/nao_milho), por periodo de data, e paginacao numerada (8 por
    pagina por padrao). Pensado pra alimentar dashboard/mapa/tabela, nao
    pra trazer o detalhe completo de cada item (isso e o GetCapturaUseCase).
    """

    def __init__(self, repository: ICapturaRepository):
        self._repository = repository

    def execute(
        self,
        plantacao_id: str = MOCK_PLANTACAO_ID,
        status_geral: str | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        pagina: int = 1,
        tamanho_pagina: int = 8,
    ) -> ListCapturasOutputDTO:
        capturas, total = self._repository.list_by_plantacao(
            plantacao_id=plantacao_id,
            status_geral=status_geral,
            data_inicio=data_inicio,
            data_fim=data_fim,
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
        )
        total_paginas = (total + tamanho_pagina - 1) // tamanho_pagina if total > 0 else 0
        return ListCapturasOutputDTO(
            capturas=[_resumo_de(c) for c in capturas],
            pagina=pagina,
            tamanho_pagina=tamanho_pagina,
            total=total,
            total_paginas=total_paginas,
        )


class GetCapturaUseCase:
    """GET especifico — detalhe completo de uma captura, incluindo URL
    assinada da imagem (o front nao precisa de credencial AWS pra exibir
    a foto — a URL ja vem pronta pra usar direto num <img src=...>)."""

    def __init__(self, repository: ICapturaRepository, storage: IStorageService):
        self._repository = repository
        self._storage = storage

    def execute(self, plantacao_id: str, timestamp: str, captura_id: str) -> CapturaDetalheDTO | None:
        captura = self._repository.get(plantacao_id, timestamp, captura_id)
        if captura is None:
            return None

        ia = captura.ia_nuvem or {}
        probabilidades = ia.get("probabilidades")
        if probabilidades is not None:
            probabilidades = {k: float(v) for k, v in probabilidades.items()}

        try:
            imagem_url = self._storage.generate_presigned_url(captura.s3_key)
        except Exception:
            # se a URL nao puder ser gerada por algum motivo, o resto do
            # detalhe ainda e util — nao derruba a resposta inteira por isso
            imagem_url = None

        return CapturaDetalheDTO(
            captura_id=captura.captura_id,
            plantacao_id=captura.plantacao_id,
            carrinho_id=captura.carrinho_id,
            cliente_id=captura.cliente_id,
            timestamp=captura.timestamp,
            status=captura.status,
            latitude=captura.coordenadas.latitude,
            longitude=captura.coordenadas.longitude,
            status_geral=ia.get("status_geral"),
            confianca_status_geral=(
                float(ia["confianca_status_geral"]) if ia.get("confianca_status_geral") is not None else None
            ),
            subtipo=ia.get("subtipo"),
            confianca_subtipo=(
                float(ia["confianca_subtipo"]) if ia.get("confianca_subtipo") is not None else None
            ),
            probabilidades=probabilidades,
            modelo_versao_borda=captura.jetson_nano.modelo_versao,
            confianca_borda=captura.jetson_nano.confianca,
            imagem_url=imagem_url,
            status_history=[
                {"status": e.status, "timestamp": e.timestamp} for e in captura.status_history
            ],
            erro_detalhes=captura.erro_detalhes,
            alerta_emitido=captura.alerta_emitido,
            alerta_emitido_em=captura.alerta_emitido_em,
        )
