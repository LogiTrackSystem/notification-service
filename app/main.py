from contextlib import asynccontextmanager
from fastapi import FastAPI

from .routers import notificaciones, preferencias
from .events import iniciar_consumidor


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await iniciar_consumidor()
    yield
    await connection.close()


app = FastAPI(title="Notification Service", lifespan=lifespan)
app.include_router(notificaciones.router)
app.include_router(preferencias.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}