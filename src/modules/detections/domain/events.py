"""
Eventos de domínio do módulo Detections.
"""

import uuid
from dataclasses import dataclass, field

from src.shared.event_bus import DomainEvent


@dataclass
class PestDetectedEvent(DomainEvent):
    """Emitido quando uma praga é identificada pelo modelo de IA."""

    detection_id: uuid.UUID = field(default_factory=uuid.uuid4)
    device_id: uuid.UUID = field(default_factory=uuid.uuid4)
    pest_name: str = ""
    confidence: float = 0.0
