from fastapi import FastAPI

from interfaces.routes import router

app = FastAPI(title="Blick API", version="0.1.0")
app.include_router(router)
