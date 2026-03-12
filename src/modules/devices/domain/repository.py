"""
Port do repositório de dispositivos.
"""

from abc import abstractmethod

from src.modules.devices.domain.entities import Device
from src.shared.base_repository import AbstractRepository


class DeviceRepositoryPort(AbstractRepository[Device]):
    """Contrato do repositório de dispositivos IoT."""

    @abstractmethod
    async def list_by_owner(
        self, owner_id: str
    ) -> list[Device]:
        """Lista dispositivos de um proprietário."""
        ...
