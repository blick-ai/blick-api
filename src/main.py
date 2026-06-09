import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interfaces.routes import auth_router, router

app = FastAPI(title="Blick API", version="0.1.0")

# CORS tratado aqui (não no API Gateway): a rota ANY /{proxy+} do HTTP API
# encaminha o preflight OPTIONS pro container, então o FastAPI precisa
# responder o OPTIONS com 2xx. Origens configuráveis via CORS_ALLOWED_ORIGINS.
_default_origins = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
allowed_origins = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)
