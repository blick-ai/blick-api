"""
Exceções de domínio do módulo Devices.
"""

from src.shared.exceptions import NotFoundException


class DeviceNotFoundException(NotFoundException):
    """Dispositivo não encontrado."""

    def __init__(self, identifier: str | None = None):
        super().__init__(
            resource="Dispositivo", identifier=identifier
        )
