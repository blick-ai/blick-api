"""
Interface genérica de repositório (Port).
"""

import uuid
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """
    Port genérico de repositório.

    Define o contrato que toda implementação concreta (Adapter)
    deve seguir.
    """

    @abstractmethod
    async def get_by_id(self, entity_id: uuid.UUID) -> T | None:
        """Retorna entidade por ID ou None."""
        ...

    @abstractmethod
    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[T]:
        """Retorna lista paginada de entidades."""
        ...

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persiste nova entidade."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Atualiza entidade existente."""
        ...

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID) -> None:
        """Remove entidade por ID."""
        ...
