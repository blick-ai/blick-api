"""
Casos de uso do módulo Users.
"""

import uuid

from src.modules.users.application.dtos import (
    UserCreateDTO,
    UserResponseDTO,
)
from src.modules.users.domain.entities import User
from src.modules.users.domain.exceptions import (
    DuplicateEmailException,
    UserNotFoundException,
)
from src.modules.users.domain.repository import UserRepositoryPort


def _to_response(user: User) -> UserResponseDTO:
    """Converte entidade User para DTO de resposta."""
    return UserResponseDTO(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


class CreateUser:
    """Caso de uso: criar um novo usuário."""

    def __init__(self, repository: UserRepositoryPort):
        self._repository = repository

    async def execute(self, dto: UserCreateDTO) -> UserResponseDTO:
        existing = await self._repository.get_by_email(dto.email)
        if existing:
            raise DuplicateEmailException(dto.email)

        user = User(
            full_name=dto.full_name,
            email=dto.email,
            role=dto.role,
            hashed_password=dto.password,  # hash real no auth
        )
        user.validate_role()
        saved = await self._repository.add(user)
        return _to_response(saved)


class GetUser:
    """Caso de uso: buscar usuário por ID."""

    def __init__(self, repository: UserRepositoryPort):
        self._repository = repository

    async def execute(self, user_id: uuid.UUID) -> UserResponseDTO:
        user = await self._repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(str(user_id))
        return _to_response(user)


class ListUsers:
    """Caso de uso: listar todos os usuários."""

    def __init__(self, repository: UserRepositoryPort):
        self._repository = repository

    async def execute(
        self, skip: int = 0, limit: int = 100
    ) -> list[UserResponseDTO]:
        users = await self._repository.list_all(
            skip=skip, limit=limit
        )
        return [_to_response(u) for u in users]
