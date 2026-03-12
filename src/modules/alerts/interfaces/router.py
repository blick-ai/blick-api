"""
Router FastAPI do módulo Alerts.
"""

from fastapi import APIRouter

router = APIRouter()

# TODO: Implementar endpoints de alertas
# GET  /              → Listar alertas (filtro: não reconhecidos)
# GET  /{alert_id}    → Buscar alerta por ID
# PATCH /{alert_id}/ack → Reconhecer alerta
