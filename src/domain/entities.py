from dataclasses import dataclass, field
from datetime import datetime
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
            "timestamp": self.timestamp,
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
            "status_history": [
                {"status": e.status, "timestamp": e.timestamp}
                for e in self.status_history
            ],
            "erro_detalhes": self.erro_detalhes,
            "alerta_emitido": self.alerta_emitido,
            "alerta_emitido_em": self.alerta_emitido_em,
            "ttl": self.ttl,
        }
