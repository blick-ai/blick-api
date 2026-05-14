from fastapi import APIRouter, Depends, HTTPException

from application.dtos import CapturaInputDTO
from application.use_cases import ListClientesUseCase, SubmitCapturaUseCase
from domain.exceptions import (
    BlickAuthError,
    BlickInvalidCredentialsError,
    BlickUserAlreadyExistsError,
    BlickUserNotConfirmedError,
)
from infrastructure.cognito_auth import CognitoAuthService
from interfaces.dependencies import (
    get_auth_service,
    get_list_clientes_use_case,
    get_submit_captura_use_case,
    oauth2_scheme,
)
from interfaces.schemas import (
    CadastroRequest,
    CapturaRequest,
    CapturaResponse,
    ConfirmarCadastroRequest,
    ListClientesResponse,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RecuperarSenhaRequest,
)

router = APIRouter()
auth_router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_cliente_id(
    token: str = Depends(oauth2_scheme),
    auth_service: CognitoAuthService = Depends(get_auth_service),
) -> str:
    try:
        return auth_service.verify_token(token)
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
    )
    result = use_case.execute(dto)
    return CapturaResponse(
        sucesso=result.sucesso,
        captura_id=result.captura_id,
        s3_key=result.s3_key,
    )


@router.get("/clientes", response_model=ListClientesResponse)
def listar_clientes(
    use_case: ListClientesUseCase = Depends(get_list_clientes_use_case),
):
    result = use_case.execute()
    return ListClientesResponse(cliente_ids=result.cliente_ids)
