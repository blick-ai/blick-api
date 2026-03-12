"""
Eventos de domínio do módulo Alerts.
"""

import uuid
from dataclasses import dataclass, field

from src.shared.event_bus import DomainEvent


@dataclass
class AlertCreatedEvent(DomainEvent):
    """Emitido quando um novo alerta é criado."""

    alert_id: uuid.UUID = field(default_factory=uuid.uuid4)
    severity: str = "medium"


@dataclass
class AlertAcknowledgedEvent(DomainEvent):
    """Emitido quando um alerta é reconhecido."""

    alert_id: uuid.UUID = field(default_factory=uuid.uuid4)
