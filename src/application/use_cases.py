import base64
import uuid
from datetime import datetime

from application.dtos import CapturaInputDTO, CapturaOutputDTO, ListClientesOutputDTO
from domain.entities import Captura, Coordenadas, JetsonNanoInfo, StatusEntry
from domain.ports import ICapturaRepository, IStorageService

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
                confianca=0.97,
                modelo_versao="ia-blick-v2",
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


class ListClientesUseCase:
    def __init__(self, repository: ICapturaRepository):
        self._repository = repository

    def execute(self) -> ListClientesOutputDTO:
        cliente_ids = self._repository.list_cliente_ids()
        return ListClientesOutputDTO(cliente_ids=cliente_ids)
