"""
Entidade Alert — alerta de praga detectada.
"""

import uuid
from datetime import datetime

from src.shared.base_entity import BaseEntity


class Alert(BaseEntity):
    """
    Representa um alerta gerado quando uma praga é detectada
    pelo modelo de IA. É enviado ao dashboard para notificar
    o produtor/técnico.
    """

    SEVERITY_LEVELS = ("low", "medium", "high", "critical")

    def __init__(
        self,
        detection_id: uuid.UUID,
        device_id: uuid.UUID,
        pest_name: str,
        severity: str = "medium",
        is_acknowledged: bool = False,
        message: str = "",
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        super().__init__(
            id=id, created_at=created_at, updated_at=updated_at
        )
        self.detection_id = detection_id
        self.device_id = device_id
        self.pest_name = pest_name
        self.severity = severity
        self.is_acknowledged = is_acknowledged
        self.message = message

    def acknowledge(self) -> None:
        """Marca o alerta como reconhecido pelo usuário."""
        self.is_acknowledged = True
