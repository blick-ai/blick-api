"""
Eventos de domínio do módulo Auth.
"""

from dataclasses import dataclass

from src.shared.event_bus import DomainEvent

# TODO: Implementar eventos de autenticação


@dataclass
class UserLoggedInEvent(DomainEvent):
    """Emitido quando um usuário faz login."""

    user_id: str = ""
