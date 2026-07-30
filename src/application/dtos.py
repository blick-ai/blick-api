from dataclasses import dataclass
from typing import Optional


@dataclass
class CapturaInputDTO:
    cliente_id: str
    dia_mes_ano: str  # formato: "dd/mm/yyyy"
    latitude: float
    longitude: float
    imagem_base64: str
    modelo_versao_borda: Optional[str] = None
    confianca_borda: Optional[float] = None


@dataclass
class CapturaOutputDTO:
    sucesso: bool
    captura_id: str
    s3_key: str


@dataclass
class ClassificacaoOutputDTO:
    captura_id: str
    status: str
    status_geral: Optional[str]
    confianca_status_geral: Optional[float]
    subtipo: Optional[str]


@dataclass
class ListClientesOutputDTO:
    cliente_ids: list[str]
