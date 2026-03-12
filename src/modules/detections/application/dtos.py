"""
DTOs do módulo Detections.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DetectionCreateDTO:
    """Dados para submeter uma nova detecção."""

    device_id: uuid.UUID
    image_url: str


@dataclass(frozen=True)
class DetectionResponseDTO:
    """Representação de saída de uma detecção."""

    id: uuid.UUID
    device_id: uuid.UUID
    image_url: str
    pest_name: str | None
    confidence: float
    is_pest_detected: bool
    created_at: datetime
    updated_at: datetime
