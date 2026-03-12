"""
Port do repositório de detecções.
"""

import uuid
from abc import abstractmethod

from src.modules.detections.domain.entities import Detection
from src.shared.base_repository import AbstractRepository


class DetectionRepositoryPort(AbstractRepository[Detection]):
    """Contrato do repositório de detecções."""

    @abstractmethod
    async def list_by_device(
        self, device_id: uuid.UUID
    ) -> list[Detection]:
        """Lista detecções de um dispositivo."""
        ...
