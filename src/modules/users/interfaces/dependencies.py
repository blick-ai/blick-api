"""
Dependências (Depends) específicas do módulo Users.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.dependencies import get_db
from src.modules.users.application.services import UserService
from src.modules.users.infrastructure.repository import (
    SqlAlchemyUserRepository,
)


def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """Injeta o UserService com o repositório concreto."""
    repository = SqlAlchemyUserRepository(db)
    return UserService(repository=repository)
