"""
DTOs do módulo Auth.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginDTO:
    """Dados para login."""

    email: str
    password: str


@dataclass(frozen=True)
class TokenResponseDTO:
    """Resposta com tokens de acesso."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
