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


class CapturaSimplesRequest(BaseModel):
    """Upload manual simplificado — só a foto, nada mais."""
    imagem_base64: str = Field(..., min_length=1)


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


class ReclassificarResponse(BaseModel):
    model_config = {"populate_by_name": True}

    pagina: int
    tamanho_pagina: int = Field(alias="tamanhoPagina")
    total: int
    total_paginas: int = Field(alias="totalPaginas")
    processadas: int
    erros: int


class ThumbnailsResponse(BaseModel):
    model_config = {"populate_by_name": True}

    pagina: int
    tamanho_pagina: int = Field(alias="tamanhoPagina")
    total: int
    total_paginas: int = Field(alias="totalPaginas")
    processadas: int
    ja_tinham: int = Field(alias="jaTinham")
    erros: int


class BackfillOrigemResponse(BaseModel):
    model_config = {"populate_by_name": True}

    pagina: int
    tamanho_pagina: int = Field(alias="tamanhoPagina")
    total: int
    total_paginas: int = Field(alias="totalPaginas")
    processadas: int
    erros: int


class DeletarCapturaResponse(BaseModel):
    model_config = {"populate_by_name": True}

    sucesso: bool
    captura_id: str = Field(alias="capturaId")


class CapturaResumoResponse(BaseModel):
    model_config = {"populate_by_name": True}

    captura_id: str = Field(alias="capturaId")
    timestamp: str
    status: str
    status_geral: Optional[str] = Field(default=None, alias="statusGeral")
    confianca_status_geral: Optional[float] = Field(default=None, alias="confiancaStatusGeral")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    alerta_emitido: bool = Field(alias="alertaEmitido")
    imagem_url: Optional[str] = Field(default=None, alias="imagemUrl")
    origem: str = "rover"


class ListCapturasResponse(BaseModel):
    model_config = {"populate_by_name": True}

    capturas: list[CapturaResumoResponse]
    pagina: int
    tamanho_pagina: int = Field(alias="tamanhoPagina")
    total: int
    total_paginas: int = Field(alias="totalPaginas")


class PontoMapaResponse(BaseModel):
    model_config = {"populate_by_name": True}

    captura_id: str = Field(alias="capturaId")
    timestamp: str
    latitude: float
    longitude: float
    status_geral: Optional[str] = Field(default=None, alias="statusGeral")


class MapaResponse(BaseModel):
    model_config = {"populate_by_name": True}

    total: int
    pontos: list[PontoMapaResponse]


class LocalizacaoResponse(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PlantaResponse(BaseModel):
    classe: Optional[str] = None
    confianca: Optional[float] = None
    aninhada: Optional[bool] = None
    # marcacao da planta na foto, coordenadas normalizadas 0..1
    # contorno: [[x, y], ...]   caixa: [x1, y1, x2, y2]
    # capturas antigas (antes das marcacoes) vem sem esses campos (None)
    contorno: Optional[list[list[float]]] = None
    caixa: Optional[list[float]] = None


class DiagnosticoResponse(BaseModel):
    model_config = {"populate_by_name": True}

    status: Optional[str] = None
    confianca: Optional[float] = None
    total_plantas: int = Field(default=0, alias="totalPlantas")
    plantas_nao_saudaveis: int = Field(default=0, alias="plantasNaoSaudaveis")


class AlertaResponse(BaseModel):
    model_config = {"populate_by_name": True}

    emitido: bool
    ultima_emissao: Optional[str] = Field(default=None, alias="ultimaEmissao")


class CapturaDetalheResponse(BaseModel):
    """
    Resposta aninhada do detalhe de uma captura. Troca a forma antiga
    (flat) por essa estrutura, pedida pelo front pra organizar melhor o
    consumo dos dados.
    """
    model_config = {"populate_by_name": True}

    captura_id: str = Field(alias="capturaId")
    capturado_em: str = Field(alias="capturadoEm")
    origem: str = "rover"
    carrinho_id: str = Field(alias="carrinhoId")
    plantacao_id: str = Field(alias="plantacaoId")
    cliente_id: str = Field(alias="clienteId")
    localizacao: LocalizacaoResponse
    status_processamento: str = Field(alias="statusProcessamento")
    diagnostico: Optional[DiagnosticoResponse] = None
    plantas: list[PlantaResponse] = Field(default_factory=list)
    alerta: AlertaResponse
    imagem_url: Optional[str] = Field(default=None, alias="imagemUrl")
    status_history: list[dict] = Field(alias="statusHistory")
    erro_detalhes: Optional[str] = Field(default=None, alias="erroDetalhes")
    modelo_versao_borda: str = Field(alias="modeloVersaoBorda")
    confianca_borda: float = Field(alias="confiancaBorda")


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
