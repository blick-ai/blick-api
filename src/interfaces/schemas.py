import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CapturaRequest(BaseModel):
    dia_mes_ano: str = Field(..., pattern=r"^\d{2}/\d{2}/\d{4}$")
    latitude: float
    longitude: float
    imagem_base64: str = Field(..., min_length=1)
    modelo_versao_borda: Optional[str] = None
    confianca_borda: Optional[float] = None


class CapturaResponse(BaseModel):
    sucesso: bool
    captura_id: str
    s3_key: str


class ClassificacaoResponse(BaseModel):
    captura_id: str
    status: str
    status_geral: Optional[str] = None
    confianca_status_geral: Optional[float] = None
    subtipo: Optional[str] = None


class PendentesResponse(BaseModel):
    total: int
    processadas: int
    erros: int


class CapturaResumoResponse(BaseModel):
    captura_id: str
    timestamp: str
    status: str
    status_geral: Optional[str] = None
    confianca_status_geral: Optional[float] = None
    latitude: float
    longitude: float
    alerta_emitido: bool


class ListCapturasResponse(BaseModel):
    capturas: list[CapturaResumoResponse]
    pagina: int
    tamanho_pagina: int
    total: int
    total_paginas: int


class CapturaDetalheResponse(BaseModel):
    captura_id: str
    plantacao_id: str
    carrinho_id: str
    cliente_id: str
    timestamp: str
    status: str
    latitude: float
    longitude: float
    status_geral: Optional[str] = None
    confianca_status_geral: Optional[float] = None
    subtipo: Optional[str] = None
    confianca_subtipo: Optional[float] = None
    probabilidades: Optional[dict] = None
    modelo_versao_borda: str
    confianca_borda: float
    imagem_url: Optional[str] = None
    status_history: list[dict]
    erro_detalhes: Optional[str] = None
    alerta_emitido: bool
    alerta_emitido_em: Optional[str] = None


class ListClientesResponse(BaseModel):
    cliente_ids: list[str]


class CadastroRequest(BaseModel):
    email: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=8)

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        if not re.search(r"[a-z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra minúscula")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Senha deve conter pelo menos uma letra maiúscula")
        if not re.search(r"\d", v):
            raise ValueError("Senha deve conter pelo menos um número")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1)
    senha: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str
    token_type: str = "bearer"


class RecuperarSenhaRequest(BaseModel):
    email: str = Field(..., min_length=1)


class ConfirmarCadastroRequest(BaseModel):
    email: str = Field(..., min_length=1)
    codigo: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    message: str
