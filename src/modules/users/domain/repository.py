"""
Port do repositório de usuários (interface).
"""

from abc import abstractmethod

from src.modules.users.domain.entities import User
from src.shared.base_repository import AbstractRepository


class UserRepositoryPort(AbstractRepository[User]):
    """
    Contrato do repositório de usuários.

    A camada de domínio depende SOMENTE desta interface.
    A implementação concreta fica em infrastructure/.
    """

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Busca usuário por e-mail."""
        ...
