from fastapi import FastAPI

from interfaces.routes import auth_router, router

app = FastAPI(title="Blick API", version="0.1.0")
app.include_router(auth_router)
app.include_router(router)
