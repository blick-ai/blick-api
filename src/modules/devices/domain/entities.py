"""
Entidade Device — nó IoT / Edge no campo.
"""

import uuid
from datetime import datetime

from src.shared.base_entity import BaseEntity


class Device(BaseEntity):
    """
    Representa um dispositivo IoT (nó Edge) instalado na fazenda.

    Responsável por capturar imagens e dados ambientais e
    enviá-los ao backend para análise.
    """

    def __init__(
        self,
        name: str,
        location: str,
        owner_id: uuid.UUID | None = None,
        is_online: bool = False,
        firmware_version: str = "",
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        super().__init__(
            id=id, created_at=created_at, updated_at=updated_at
        )
        self.name = name
        self.location = location
        self.owner_id = owner_id
        self.is_online = is_online
        self.firmware_version = firmware_version
