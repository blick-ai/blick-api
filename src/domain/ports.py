from abc import ABC, abstractmethod

from domain.entities import Captura


class IStorageService(ABC):
    @abstractmethod
    def upload_image(self, key: str, image_bytes: bytes) -> None:
        ...


class ICapturaRepository(ABC):
    @abstractmethod
    def save(self, captura: Captura) -> None:
        ...
