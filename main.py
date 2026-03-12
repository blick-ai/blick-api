"""
BLICK Backend — Entrypoint da aplicação.

Execute com:
    uvicorn main:app --reload
"""

from src.config.app_factory import create_app

app = create_app()
