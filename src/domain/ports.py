from abc import ABC, abstractmethod

from domain.entities import Captura, ClassificacaoResultado


class IStorageService(ABC):
    @abstractmethod
    def upload_image(self, key: str, image_bytes: bytes) -> None:
        ...

    @abstractmethod
    def download_image(self, key: str) -> bytes:
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
    def list_by_status(self, status: str, limit: int = 50) -> list[Captura]:
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