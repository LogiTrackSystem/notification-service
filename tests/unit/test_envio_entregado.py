"""Unitaria 2: events._procesar_shipment_delivered registra la notificación de entrega."""
import asyncio

from app import events
from app.store import listar_notificaciones


def test_envio_entregado_registra_notificacion_por_email(envios):
    # Arrange: Shipment (simulado) devuelve el cliente del envío
    envios["e-1"] = {"cliente_id": "cliente-1"}
    payload = {"envio_id": "e-1", "nombre_receptor": "Ana", "entregado_en": "2026-11-16"}
    # Act
    asyncio.run(events._procesar_shipment_delivered(payload))
    # Assert
    n = listar_notificaciones()[0]
    assert n["evento_origen"] == "shipment.delivered" and n["canal"] == "email"
    assert "Ana" in n["mensaje"]
