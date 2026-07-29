from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from application.dtos import CapturaInputDTO
from application.use_cases import (
    ClassifyCapturaUseCase,
    ClassifyPendentesUseCase,
    ListClientesUseCase,
    SubmitCapturaUseCase,
)
from domain.exceptions import (
    BlickAuthError,
    BlickInvalidCredentialsError,
    BlickUserAlreadyExistsError,
    BlickUserNotConfirmedError,
)
from infrastructure.cognito_auth import CognitoAuthService
from interfaces.dependencies import (
    get_auth_service,
    get_classify_captura_use_case,
    get_classify_pendentes_use_case,
    get_list_clientes_use_case,
    get_submit_captura_use_case,
    security,
)
from interfaces.schemas import (
    CadastroRequest,
    CapturaRequest,
    CapturaResponse,
    ClassificacaoResponse,
    ConfirmarCadastroRequest,
    ListClientesResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PendentesResponse,
    RecuperarSenhaRequest,
)

router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_cliente_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: CognitoAuthService = Depends(get_auth_service),
) -> str:
    try:
        return auth_service.verify_token(credentials.credentials)
    except BlickAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@auth_router.post("/cadastro", response_model=MessageResponse, status_code=201)
def cadastrar(
    body: CadastroRequest,
    auth_service: CognitoAuthService = Depends(get_auth_service),
):
    try:
        auth_service.cadastrar(body.email, body.senha)
        return MessageResponse(
            message="Cadastro realizado. Verifique seu email para confirmar.",
        )
    except BlickUserAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Usuário já cadastrado")
    except BlickAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    auth_service: CognitoAuthService = Depends(get_auth_service),
):
    try:
        tokens = auth_service.login(body.email, body.senha)
        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            id_token=tokens["id_token"],
        )
    except BlickInvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    except BlickUserNotConfirmedError:
        raise HTTPException(status_code=403, detail="Usuário não confirmado")
    except BlickAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/recuperar-senha", response_model=MessageResponse)
def recuperar_senha(
    body: RecuperarSenhaRequest,
    auth_service: CognitoAuthService = Depends(get_auth_service),
):
    try:
        auth_service.recuperar_senha(body.email)
        return MessageResponse(
            message="Código de recuperação enviado para o email.",
        )
    except BlickAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/confirmar-cadastro", response_model=MessageResponse)
def confirmar_cadastro(
    body: ConfirmarCadastroRequest,
    auth_service: CognitoAuthService = Depends(get_auth_service),
):
    try:
        auth_service.confirmar_cadastro(body.email, body.codigo)
        return MessageResponse(message="Cadastro confirmado com sucesso.")
    except BlickAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/capturas", response_model=CapturaResponse, status_code=201)
def criar_captura(
    body: CapturaRequest,
    cliente_id: str = Depends(get_current_cliente_id),
    use_case: SubmitCapturaUseCase = Depends(get_submit_captura_use_case),
):
    dto = CapturaInputDTO(
        cliente_id=cliente_id,
        dia_mes_ano=body.dia_mes_ano,
        latitude=body.latitude,
        longitude=body.longitude,
        imagem_base64=body.imagem_base64,
        modelo_versao_borda=body.modelo_versao_borda,
        confianca_borda=body.confianca_borda,
    )
    result = use_case.execute(dto)
    return CapturaResponse(
        sucesso=result.sucesso,
        captura_id=result.captura_id,
        s3_key=result.s3_key,
    )


@router.post("/capturas/{captura_id}/classificar", response_model=ClassificacaoResponse)
def classificar_captura(
    captura_id: str,
    timestamp: str,
    plantacao_id: str = "plantacao-mock-001",
    cliente_id: str = Depends(get_current_cliente_id),
    use_case: ClassifyCapturaUseCase = Depends(get_classify_captura_use_case),
):
    try:
        captura = use_case.execute(plantacao_id, timestamp, captura_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Falha ao classificar: {e}")

    ia = captura.ia_nuvem or {}
    confianca_str = ia.get("confianca_status_geral")
    return ClassificacaoResponse(
        captura_id=captura.captura_id,
        status=captura.status,
        status_geral=ia.get("status_geral"),
        confianca_status_geral=float(confianca_str) if confianca_str is not None else None,
        subtipo=ia.get("subtipo"),
    )


@router.post("/capturas/classificar-pendentes", response_model=PendentesResponse)
def classificar_pendentes(
    limite: int = 50,
    cliente_id: str = Depends(get_current_cliente_id),
    use_case: ClassifyPendentesUseCase = Depends(get_classify_pendentes_use_case),
):
    resultado = use_case.execute(limite=limite)
    return PendentesResponse(**resultado)


@router.get("/clientes", response_model=ListClientesResponse)
def listar_clientes(
    use_case: ListClientesUseCase = Depends(get_list_clientes_use_case),
):
    result = use_case.execute()
    return ListClientesResponse(cliente_ids=result.cliente_ids)
