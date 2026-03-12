"""
Entidade User — núcleo do módulo de usuários.
"""

import uuid
from datetime import datetime

from src.shared.base_entity import BaseEntity


class User(BaseEntity):
    """
    Representa um usuário do sistema BLICK.

    Pode ser um produtor rural, técnico agrícola ou administrador.
    """

    def __init__(
        self,
        full_name: str,
        email: str,
        role: str = "producer",
        is_active: bool = True,
        hashed_password: str = "",
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.full_name = full_name
        self.email = email
        self.role = role
        self.is_active = is_active
        self.hashed_password = hashed_password

    VALID_ROLES = ("admin", "technician", "producer")

    def validate_role(self) -> None:
        """Garante que o role é válido."""
        if self.role not in self.VALID_ROLES:
            raise ValueError(
                f"Role '{self.role}' inválido. "
                f"Esperado: {self.VALID_ROLES}"
            )

    def deactivate(self) -> None:
        """Desativa a conta do usuário."""
        self.is_active = False

    def activate(self) -> None:
        """Reativa a conta do usuário."""
        self.is_active = True
