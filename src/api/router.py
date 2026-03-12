"""
Router principal da API — agrega routers de todos os módulos.
"""

from fastapi import APIRouter

from src.modules.users.interfaces.router import router as users_router
from src.modules.auth.interfaces.router import router as auth_router
from src.modules.devices.interfaces.router import router as devices_router
from src.modules.detections.interfaces.router import (
    router as detections_router,
)
from src.modules.alerts.interfaces.router import router as alerts_router

api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(
    devices_router, prefix="/devices", tags=["Devices"]
)
api_router.include_router(
    detections_router, prefix="/detections", tags=["Detections"]
)
api_router.include_router(
    alerts_router, prefix="/alerts", tags=["Alerts"]
)
