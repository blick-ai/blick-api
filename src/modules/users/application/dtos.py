"""
DTOs (Data Transfer Objects) do módulo Users.

Objetos usados para transferir dados entre as camadas
application e interfaces, sem expor a entidade diretamente.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserCreateDTO:
    """Dados necessários para criar um novo usuário."""

    full_name: str
    email: str
    password: str
    role: str = "producer"


@dataclass(frozen=True)
class UserUpdateDTO:
    """Dados opcionais para atualizar um usuário."""

    full_name: str | None = None
    email: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class UserResponseDTO:
    """Representação de saída do usuário."""

    id: uuid.UUID
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
