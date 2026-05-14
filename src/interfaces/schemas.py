from pydantic import BaseModel, Field


class CapturaRequest(BaseModel):
    cliente_id: str = Field(..., min_length=1)
    dia_mes_ano: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    latitude: float
    longitude: float
    imagem_base64: str = Field(..., min_length=1)


class CapturaResponse(BaseModel):
    sucesso: bool
    captura_id: str
    s3_key: str


class ListClientesResponse(BaseModel):
    cliente_ids: list[str]
