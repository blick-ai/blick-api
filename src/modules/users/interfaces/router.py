"""
Router FastAPI do módulo Users.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.users.application.dtos import UserCreateDTO
from src.modules.users.application.services import UserService
from src.modules.users.interfaces.dependencies import (
    get_user_service,
)
from src.modules.users.interfaces.schemas import (
    UserCreateRequest,
    UserListResponse,
    UserResponse,
)
from src.shared.exceptions import ConflictException, NotFoundException

router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo usuário",
)
async def create_user(
    body: UserCreateRequest,
    service: UserService = Depends(get_user_service),
):
    """Cria um novo usuário no sistema BLICK."""
    try:
        dto = UserCreateDTO(
            full_name=body.full_name,
            email=body.email,
            password=body.password,
            role=body.role,
        )
        result = await service.create_user(dto)
        return result
    except ConflictException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Buscar usuário por ID",
)
async def get_user(
    user_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
):
    """Retorna os dados de um usuário específico."""
    try:
        return await service.get_user(user_id)
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        )


@router.get(
    "/",
    response_model=UserListResponse,
    summary="Listar usuários",
)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    service: UserService = Depends(get_user_service),
):
    """Retorna lista paginada de usuários."""
    users = await service.list_users(skip=skip, limit=limit)
    return UserListResponse(items=users, total=len(users))
