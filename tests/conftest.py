"""Pruebas de Notification (sin RabbitMQ ni Shipment). Su estado vive en memoria: se limpia en cada prueba."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app import events, preferencias, store
from app.main import app


@pytest.fixture(autouse=True)
def estado_limpio(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)  # un .env local no debe afectar a las pruebas
    store._notificaciones.clear()
    preferencias._preferencias.clear()
    yield
    store._notificaciones.clear()
    preferencias._preferencias.clear()


@pytest.fixture()
def envios(monkeypatch):
    """Doble de Shipment: diccionario {envio_id: envío}. Un id ausente simula Shipment caído o envío inexistente."""
    datos = {}

    async def falso(envio_id):
        return datos.get(envio_id)

    monkeypatch.setattr(events, "_obtener_envio", falso)
    return datos


@pytest.fixture()
def api():
    # sin 'with': no se ejecuta el arranque (conexión a RabbitMQ)
    return TestClient(app)
