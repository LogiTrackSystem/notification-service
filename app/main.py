import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .interno import proteger_servicio

from .routers import notificaciones, preferencias
from .events import iniciar_consumidor


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection = await iniciar_consumidor()
    yield
    await connection.close()


app = FastAPI(title="Notification Service", lifespan=lifespan)
app.include_router(notificaciones.router)
proteger_servicio(app)
app.include_router(preferencias.router)


# Métricas para Prometheus (GET /metrics): peticiones por método/estado y tiempos de respuesta
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service", "version": os.getenv("APP_VERSION", "dev")}