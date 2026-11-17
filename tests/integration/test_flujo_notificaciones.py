"""Integración: preferencia por API -> evento de entrega -> notificación visible por API."""
import asyncio

from app import events


def test_preferencia_y_evento_generan_notificacion_en_el_canal_elegido(api, envios):
    # Arrange: el cliente prefiere SMS (POST) y Shipment (simulado) lo asocia al envío
    assert api.post("/preferencias/cliente-1", json={"idioma": "es", "canal_preferido": "sms"}).status_code == 200
    envios["e-1"] = {"cliente_id": "cliente-1"}
    # Act: llega el evento y se consulta la API
    asyncio.run(events._procesar_shipment_delivered({"envio_id": "e-1", "nombre_receptor": "Ana", "entregado_en": "hoy"}))
    r = api.get("/notificaciones/")
    # Assert
    assert r.status_code == 200
    assert r.json()[0]["canal"] == "sms" and r.json()[0]["evento_origen"] == "shipment.delivered"
