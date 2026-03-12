"""
Port do repositório de autenticação.
"""

from abc import ABC, abstractmethod


class AuthRepositoryPort(ABC):
    """Contrato do repositório de autenticação."""

    @abstractmethod
    async def save_refresh_token(
        self, user_id: str, token: str
    ) -> None:
        ...

    @abstractmethod
    async def revoke_refresh_token(self, token: str) -> None:
        ...
