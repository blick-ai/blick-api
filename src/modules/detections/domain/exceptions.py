"""
Exceções de domínio do módulo Detections.
"""

from src.shared.exceptions import DomainException, NotFoundException


class DetectionNotFoundException(NotFoundException):
    """Detecção não encontrada."""

    def __init__(self, identifier: str | None = None):
        super().__init__(
            resource="Detecção", identifier=identifier
        )


class ImageProcessingException(DomainException):
    """Erro ao processar imagem para análise."""

    def __init__(self, message: str = "Erro ao processar imagem"):
        super().__init__(message=message)
