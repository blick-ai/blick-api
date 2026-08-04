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
class CapturaResumoDTO:
    """Item enxuto pra listagem — só o que faz sentido numa tabela/mapa."""
    captura_id: str
    timestamp: str
    status: str
    status_geral: Optional[str]
    confianca_status_geral: Optional[float]
    latitude: float
    longitude: float
    alerta_emitido: bool


@dataclass
class ListCapturasOutputDTO:
    capturas: list[CapturaResumoDTO]
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int


@dataclass
class CapturaDetalheDTO:
    """Tudo — pra tela de detalhe de uma captura específica."""
    captura_id: str
    plantacao_id: str
    carrinho_id: str
    cliente_id: str
    timestamp: str
    status: str
    latitude: float
    longitude: float
    status_geral: Optional[str]
    confianca_status_geral: Optional[float]
    subtipo: Optional[str]
    confianca_subtipo: Optional[float]
    probabilidades: Optional[dict]
    modelo_versao_borda: str
    confianca_borda: float
    imagem_url: Optional[str]
    status_history: list[dict]
    erro_detalhes: Optional[str]
    alerta_emitido: bool
    alerta_emitido_em: Optional[str]


@dataclass
class ListClientesOutputDTO:
    cliente_ids: list[str]
