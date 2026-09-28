import json
import logging
import os

import aio_pika
import httpx
from dotenv import load_dotenv

from .store import registrar_notificacion

load_dotenv()

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
SHIPMENT_SERVICE_URL = os.getenv("SHIPMENT_SERVICE_URL")
EXCHANGE_NAME = "logitrack_events"

logger = logging.getLogger("notification-service")

ROUTING_KEYS = [
    "route.assigned",
    "shipment.delivered",
    "shipment.incident",
    "shipment.returned",
    "maintenance.alert",
]


async def _obtener_envio(envio_id: str):
    if not SHIPMENT_SERVICE_URL:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{SHIPMENT_SERVICE_URL}/envios/{envio_id}")
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return None


async def _procesar_route_assigned(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    mensaje = (
        f"Tu envío {payload['envio_id']} fue asignado a un vehículo "
        f"(vehiculo_id={payload.get('vehiculo_id')}). La hora estimada de llegada "
        f"se confirmará más adelante."
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal="push",
        mensaje=mensaje,
        evento_origen="route.assigned",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id, "ruta_id": payload.get("ruta_id")},
    )


async def _procesar_shipment_delivered(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    mensaje = (
        f"Tu envío {payload['envio_id']} fue entregado a "
        f"{payload.get('nombre_receptor')} el {payload.get('entregado_en')}."
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal="email",
        mensaje=mensaje,
        evento_origen="shipment.delivered",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id},
    )


async def _procesar_shipment_incident(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    mensaje = f"Se reportó una incidencia en tu envío {payload['envio_id']}: {payload.get('notas') or 'sin detalle'}."
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal="sms",
        mensaje=mensaje,
        evento_origen="shipment.incident",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id},
    )


async def _procesar_shipment_returned(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    mensaje = f"Tu envío {payload['envio_id']} fue devuelto. Motivo: {payload.get('notas') or 'sin detalle'}."
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal="email",
        mensaje=mensaje,
        evento_origen="shipment.returned",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id},
    )


async def _procesar_maintenance_alert(payload: dict):
    mensaje = (
        f"Alerta de mantenimiento para el vehículo {payload.get('vehiculo_id')}: "
        f"{payload.get('motivo')} (prioridad {payload.get('prioridad')})."
    )
    registrar_notificacion(
        destinatario_tipo="gestor_flota",
        canal="push",
        mensaje=mensaje,
        evento_origen="maintenance.alert",
        referencia={"vehiculo_id": payload.get("vehiculo_id"), "motivo": payload.get("motivo")},
    )


_HANDLERS = {
    "route.assigned": _procesar_route_assigned,
    "shipment.delivered": _procesar_shipment_delivered,
    "shipment.incident": _procesar_shipment_incident,
    "shipment.returned": _procesar_shipment_returned,
    "maintenance.alert": _procesar_maintenance_alert,
}


async def _on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        payload = json.loads(message.body.decode())
        handler = _HANDLERS.get(message.routing_key)
        if handler:
            try:
                await handler(payload)
            except Exception:
                logger.exception("Error procesando evento %s", message.routing_key)


async def iniciar_consumidor():
    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue("notification_service.eventos", durable=True)
    for routing_key in ROUTING_KEYS:
        await queue.bind(exchange, routing_key=routing_key)
    await queue.consume(_on_message)
    return connection