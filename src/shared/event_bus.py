"""
Barramento de eventos de domínio (in-process).

Permite que módulos publiquem e assinem eventos sem acoplamento direto.
"""

from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.shared.helpers import utc_now


@dataclass
class DomainEvent:
    """Classe base para eventos de domínio."""

    occurred_at: datetime = field(default_factory=utc_now)


# Tipo de handler assíncrono
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """
    Barramento simples de eventos de domínio.

    Uso:
        bus = EventBus()
        bus.subscribe(UserCreatedEvent, handle_user_created)
        await bus.publish(UserCreatedEvent(user_id=...))
    """

    def __init__(self) -> None:
        self._handlers: dict[
            type[DomainEvent], list[EventHandler]
        ] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        """Registra handler para um tipo de evento."""
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Dispara todos os handlers registrados."""
        for handler in self._handlers[type(event)]:
            await handler(event)


# Instância global do barramento
event_bus = EventBus()
