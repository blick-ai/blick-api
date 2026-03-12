"""
DTOs do módulo Devices.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DeviceCreateDTO:
    """Dados para registrar um novo dispositivo."""

    name: str
    location: str
    owner_id: uuid.UUID
    firmware_version: str = ""


@dataclass(frozen=True)
class DeviceResponseDTO:
    """Representação de saída de um dispositivo."""

    id: uuid.UUID
    name: str
    location: str
    owner_id: uuid.UUID | None
    is_online: bool
    firmware_version: str
    created_at: datetime
    updated_at: datetime
