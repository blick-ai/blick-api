"""
Port do repositório de alertas.
"""

from abc import abstractmethod

from src.modules.alerts.domain.entities import Alert
from src.shared.base_repository import AbstractRepository


class AlertRepositoryPort(AbstractRepository[Alert]):
    """Contrato do repositório de alertas."""

    @abstractmethod
    async def list_unacknowledged(self) -> list[Alert]:
        """Lista alertas não reconhecidos."""
        ...
