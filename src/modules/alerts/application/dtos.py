"""
DTOs do módulo Alerts.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlertCreateDTO:
    """Dados para criar um novo alerta."""

    detection_id: uuid.UUID
    device_id: uuid.UUID
    pest_name: str
    severity: str = "medium"
    message: str = ""


@dataclass(frozen=True)
class AlertResponseDTO:
    """Representação de saída de um alerta."""

    id: uuid.UUID
    detection_id: uuid.UUID
    device_id: uuid.UUID
    pest_name: str
    severity: str
    is_acknowledged: bool
    message: str
    created_at: datetime
    updated_at: datetime
