"""
Utilitários e helpers genéricos.
"""

import re
import unicodedata
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Retorna o datetime atual em UTC."""
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """Converte texto para slug (minúsculas, hifens)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)
