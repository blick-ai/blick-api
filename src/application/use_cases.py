import base64
import uuid
from datetime import datetime

from application.dtos import CapturaInputDTO, CapturaOutputDTO, ListClientesOutputDTO
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
