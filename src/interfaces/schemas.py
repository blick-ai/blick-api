import re

from pydantic import BaseModel, Field, field_validator


class CapturaRequest(BaseModel):
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
