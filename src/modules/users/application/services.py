"""
Serviço de aplicação do módulo Users.

Orquestra os casos de uso e serve como fachada
para a camada de interfaces.
"""

import uuid

from src.modules.users.application.dtos import (
    UserCreateDTO,
    UserResponseDTO,
)
from src.modules.users.application.use_cases import (
    CreateUser,
    GetUser,
    ListUsers,
)
from src.modules.users.domain.repository import UserRepositoryPort


class UserService:
    """Fachada que agrupa os casos de uso de usuários."""

    def __init__(self, repository: UserRepositoryPort):
        self._repository = repository

    async def create_user(
        self, dto: UserCreateDTO
    ) -> UserResponseDTO:
        return await CreateUser(self._repository).execute(dto)

    async def get_user(
        self, user_id: uuid.UUID
    ) -> UserResponseDTO:
        return await GetUser(self._repository).execute(user_id)

    async def list_users(
        self, skip: int = 0, limit: int = 100
    ) -> list[UserResponseDTO]:
        return await ListUsers(self._repository).execute(
            skip=skip, limit=limit
        )
