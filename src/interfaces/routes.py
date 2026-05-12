from fastapi import APIRouter, Depends

from application.dtos import CapturaInputDTO
from application.use_cases import SubmitCapturaUseCase
from interfaces.dependencies import get_submit_captura_use_case
from interfaces.schemas import CapturaRequest, CapturaResponse

router = APIRouter()


@router.post("/capturas", response_model=CapturaResponse, status_code=201)
def criar_captura(
    body: CapturaRequest,
    use_case: SubmitCapturaUseCase = Depends(get_submit_captura_use_case),
):
    dto = CapturaInputDTO(
        cliente_id=body.cliente_id,
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
