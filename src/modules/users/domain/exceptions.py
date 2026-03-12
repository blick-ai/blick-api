"""
Exceções de domínio específicas do módulo Users.
"""

from src.shared.exceptions import ConflictException, NotFoundException


class UserNotFoundException(NotFoundException):
    """Usuário não encontrado."""

    def __init__(self, identifier: str | None = None):
        super().__init__(resource="Usuário", identifier=identifier)


class DuplicateEmailException(ConflictException):
    """E-mail já cadastrado no sistema."""

    def __init__(self, email: str):
        super().__init__(
            message=f"E-mail '{email}' já está em uso"
        )
