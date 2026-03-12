"""
Exceções de domínio do módulo Auth.
"""

from src.shared.exceptions import UnauthorizedException


class InvalidCredentialsException(UnauthorizedException):
    """Credenciais de login inválidas."""

    def __init__(self):
        super().__init__(message="E-mail ou senha incorretos")


class TokenExpiredException(UnauthorizedException):
    """Token expirado ou revogado."""

    def __init__(self):
        super().__init__(message="Token expirado ou inválido")
