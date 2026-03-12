"""
Eventos de domínio do módulo Users.
"""

import uuid
from dataclasses import dataclass, field

from src.shared.event_bus import DomainEvent


@dataclass
class UserCreatedEvent(DomainEvent):
    """Emitido quando um novo usuário é criado."""

    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = ""


@dataclass
class UserDeactivatedEvent(DomainEvent):
    """Emitido quando um usuário é desativado."""

    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
