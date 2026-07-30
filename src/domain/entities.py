from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class Coordenadas:
    latitude: float
    longitude: float


@dataclass
class JetsonNanoInfo:
    planta_detectada: bool
    confianca: float
    modelo_versao: str


@dataclass
class StatusEntry:
    status: str
    timestamp: str


@dataclass
class ClassificacaoResultado:
    """Resultado devolvido pelo modelo de nuvem (via IClassificationService)."""
    status_geral: str  # "saudavel" | "praga" | "doenca" | "nao_milho"
    confianca_status_geral: float
    probabilidades: dict[str, float]
    subtipo: Optional[str] = None
    confianca_subtipo: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "status_geral": self.status_geral,
            "confianca_status_geral": Decimal(str(round(self.confianca_status_geral, 4))),
            "probabilidades": {
                k: Decimal(str(round(v, 4))) for k, v in self.probabilidades.items()
            },
            "subtipo": self.subtipo,
            "confianca_subtipo": (
                Decimal(str(round(self.confianca_subtipo, 4)))
                if self.confianca_subtipo is not None else None
            ),
        }


@dataclass
class Captura:
    captura_id: str
    cliente_id: str
    plantacao_id: str
    carrinho_id: str
    timestamp: str
    coordenadas: Coordenadas
    s3_bucket: str
    s3_key: str
    jetson_nano: JetsonNanoInfo
    status: str = "PENDENTE"
    ia_nuvem: Optional[dict] = None
    status_history: list[StatusEntry] = field(default_factory=list)
    erro_detalhes: Optional[str] = None
    alerta_emitido: bool = False
    alerta_emitido_em: Optional[str] = None
    ttl: Optional[int] = None

    @property
    def pk(self) -> str:
        return f"PLANT#{self.plantacao_id}"

    @property
    def sk(self) -> str:
        return f"CAPTURA#{self.timestamp}#{self.captura_id}"

    @property
    def gsi1pk(self) -> str:
        return f"CART#{self.carrinho_id}"

    @property
    def gsi1sk(self) -> str:
        return f"CAPTURA#{self.timestamp}"

    @property
    def gsi2pk(self) -> str:
        return f"STATUS#{self.status}"

    @property
    def gsi2sk(self) -> str:
        return self.timestamp

    def to_dynamo_item(self) -> dict:
        return {
            "PK": self.pk,
            "SK": self.sk,
            "GSI1PK": self.gsi1pk,
            "GSI1SK": self.gsi1sk,
            "GSI2PK": self.gsi2pk,
            "GSI2SK": self.gsi2sk,
            "entity_type": "CAPTURA",
            "captura_id": self.captura_id,
            "cliente_id": self.cliente_id,
            "plantacao_id": self.plantacao_id,
            "carrinho_id": self.carrinho_id,
            "coordenadas": {
                "latitude": Decimal(str(self.coordenadas.latitude)),
                "longitude": Decimal(str(self.coordenadas.longitude)),
            },
            "s3_bucket": self.s3_bucket,
            "s3_key": self.s3_key,
            "jetson_nano": {
                "planta_detectada": self.jetson_nano.planta_detectada,
                "confianca": Decimal(str(self.jetson_nano.confianca)),
                "modelo_versao": self.jetson_nano.modelo_versao,
            },
            "ia_nuvem": self.ia_nuvem,
            "status": self.status,
            "timestamp": self.timestamp,
            "status_history": [
                {"status": e.status, "timestamp": e.timestamp}
                for e in self.status_history
            ],
            "erro_detalhes": self.erro_detalhes,
            "alerta_emitido": self.alerta_emitido,
            "alerta_emitido_em": self.alerta_emitido_em,
            "ttl": self.ttl,
        }

    @staticmethod
    def from_dynamo_item(item: dict) -> "Captura":
        coord = item["coordenadas"]
        jetson = item["jetson_nano"]
        return Captura(
            captura_id=item["captura_id"],
            cliente_id=item["cliente_id"],
            plantacao_id=item["plantacao_id"],
            carrinho_id=item["carrinho_id"],
            timestamp=item["timestamp"],
            coordenadas=Coordenadas(
                latitude=float(coord["latitude"]),
                longitude=float(coord["longitude"]),
            ),
            s3_bucket=item["s3_bucket"],
            s3_key=item["s3_key"],
            jetson_nano=JetsonNanoInfo(
                planta_detectada=jetson["planta_detectada"],
                confianca=float(jetson["confianca"]),
                modelo_versao=jetson["modelo_versao"],
            ),
            status=item.get("status", "PENDENTE"),
            ia_nuvem=item.get("ia_nuvem"),
            status_history=[
                StatusEntry(status=e["status"], timestamp=e["timestamp"])
                for e in item.get("status_history", [])
            ],
            erro_detalhes=item.get("erro_detalhes"),
            alerta_emitido=item.get("alerta_emitido", False),
            alerta_emitido_em=item.get("alerta_emitido_em"),
            ttl=item.get("ttl"),
        )
