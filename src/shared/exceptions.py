"""
Exceções genéricas compartilhadas entre módulos.
"""


class DomainException(Exception):
    """Exceção base para erros de domínio."""

    def __init__(self, message: str = "Erro de domínio"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(DomainException):
    """Recurso não encontrado."""

    def __init__(
        self,
        resource: str = "Recurso",
        identifier: str | None = None,
    ):
        detail = f"{resource} não encontrado"
        if identifier:
            detail = f"{resource} com id '{identifier}' não encontrado"
        super().__init__(message=detail)


class ConflictException(DomainException):
    """Conflito — recurso já existe."""

    def __init__(self, message: str = "Recurso já existe"):
        super().__init__(message=message)


class UnauthorizedException(DomainException):
    """Não autorizado."""

    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message=message)


class ForbiddenException(DomainException):
    """Acesso negado."""

    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message=message)
