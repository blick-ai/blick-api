from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import Captura, ClassificacaoResultado


class IStorageService(ABC):
    @abstractmethod
    def upload_image(self, key: str, image_bytes: bytes) -> None:
        ...

    @abstractmethod
    def download_image(self, key: str) -> bytes:
        ...

    @abstractmethod
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        ...


class ICapturaRepository(ABC):
    @abstractmethod
    def save(self, captura: Captura) -> None:
        ...

    @abstractmethod
    def get(self, plantacao_id: str, timestamp: str, captura_id: str) -> Captura | None:
        ...

    @abstractmethod
    def update(self, captura: Captura) -> None:
        ...

    @abstractmethod
    def list_by_status(
        self, status: str, plantacao_id: str = "plantacao-mock-001", limit: int = 50
    ) -> list[Captura]:
        ...

    @abstractmethod
    def list_by_plantacao(
        self,
        plantacao_id: str,
        status: Optional[str] = None,
        status_geral: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        pagina: int = 1,
        tamanho_pagina: int = 8,
    ) -> tuple[list[Captura], int]:
        """Retorna (capturas_da_pagina, total_de_capturas_no_filtro), mais
        recentes primeiro por padrao."""
        ...

    @abstractmethod
    def list_cliente_ids(self) -> list[str]:
        ...


class IClassificationService(ABC):
    @abstractmethod
    def classify(self, image_bytes: bytes) -> ClassificacaoResultado:
        ...


class IAuthService(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> str:
        """Valida JWT e retorna cliente_id (sub)."""
        ...

    @abstractmethod
    def cadastrar(self, email: str, senha: str) -> None:
        ...

    @abstractmethod
    def login(self, email: str, senha: str) -> dict:
        """Retorna dict com access_token, refresh_token, id_token."""
        ...

    @abstractmethod
    def recuperar_senha(self, email: str) -> None:
        ...

    @abstractmethod
    def confirmar_cadastro(self, email: str, codigo: str) -> None:
        ...
