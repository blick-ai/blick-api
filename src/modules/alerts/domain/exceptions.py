"""
Exceções de domínio do módulo Alerts.
"""

from src.shared.exceptions import NotFoundException


class AlertNotFoundException(NotFoundException):
    """Alerta não encontrado."""

    def __init__(self, identifier: str | None = None):
        super().__init__(
            resource="Alerta", identifier=identifier
        )
