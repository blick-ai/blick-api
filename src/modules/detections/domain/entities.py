"""
Entidade Detection — resultado da análise de IA.
"""

import uuid
from datetime import datetime

from src.shared.base_entity import BaseEntity


class Detection(BaseEntity):
    """
    Representa uma detecção de praga resultante da análise
    de uma imagem enviada por um dispositivo IoT.
    """

    def __init__(
        self,
        device_id: uuid.UUID,
        image_url: str,
        pest_name: str | None = None,
        confidence: float = 0.0,
        is_pest_detected: bool = False,
        id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        super().__init__(
            id=id, created_at=created_at, updated_at=updated_at
        )
        self.device_id = device_id
        self.image_url = image_url
        self.pest_name = pest_name
        self.confidence = confidence
        self.is_pest_detected = is_pest_detected
