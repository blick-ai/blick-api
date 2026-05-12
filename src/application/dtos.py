from dataclasses import dataclass


@dataclass
class CapturaInputDTO:
    cliente_id: str
    dia_mes_ano: str  # formato: "dd/mm/yyyy"
    latitude: float
    longitude: float
    imagem_base64: str


@dataclass
class CapturaOutputDTO:
    sucesso: bool
    captura_id: str
    s3_key: str
