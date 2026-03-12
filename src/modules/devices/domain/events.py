"""
Eventos de domínio do módulo Devices.
"""

import uuid
from dataclasses import dataclass, field

from src.shared.event_bus import DomainEvent


@dataclass
class DeviceRegisteredEvent(DomainEvent):
    """Emitido quando um novo dispositivo é registrado."""

    device_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class DeviceOfflineEvent(DomainEvent):
    """Emitido quando um dispositivo fica offline."""

    device_id: uuid.UUID = field(default_factory=uuid.uuid4)
