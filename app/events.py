import json
import logging
import os

import aio_pika
import httpx
from dotenv import load_dotenv

from .store import registrar_notificacion
from .preferencias import obtener_preferencia

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


def _resolver_canal(cliente_id, canal_por_defecto: str) -> tuple[str, str]:
    """Cierra el hueco de 'plantillas configurables por idioma y canal':
    si el cliente tiene una preferencia configurada (POST /preferencias/{cliente_id}),
    se usa su canal preferido en vez del canal fijo por tipo de evento.
    El idioma queda registrado en la referencia, listo para cuando el
    equipo agregue plantillas en otros idiomas además de español."""
    if not cliente_id:
        return canal_por_defecto, "es"
    preferencia = obtener_preferencia(str(cliente_id))
    canal = preferencia.get("canal_preferido") or canal_por_defecto
    idioma = preferencia.get("idioma") or "es"
    return canal, idioma


async def _procesar_route_assigned(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    canal, idioma = _resolver_canal(cliente_id, "push")
    mensaje = (
        f"¡Buenas noticias! Tu envío {payload['envio_id']} ya fue asignado a un vehículo "
        f"de nuestra flota. Te avisaremos en cuanto tengamos una hora estimada de llegada."
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal=canal,
        mensaje=mensaje,
        evento_origen="route.assigned",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id, "ruta_id": payload.get("ruta_id"), "idioma": idioma},
    )


async def _procesar_shipment_delivered(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    canal, idioma = _resolver_canal(cliente_id, "email")
    mensaje = (
        f"Tu envío {payload['envio_id']} fue entregado con éxito a "
        f"{payload.get('nombre_receptor')} el {payload.get('entregado_en')}. "
        f"¡Gracias por confiar en LogiTrack!"
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal=canal,
        mensaje=mensaje,
        evento_origen="shipment.delivered",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id, "idioma": idioma},
    )


async def _procesar_shipment_incident(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    canal, idioma = _resolver_canal(cliente_id, "sms")
    mensaje = (
        f"Detectamos una incidencia con tu envío {payload['envio_id']}: "
        f"{payload.get('notas') or 'estamos revisando los detalles'}. "
        f"Nuestro equipo ya está trabajando para resolverlo."
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal=canal,
        mensaje=mensaje,
        evento_origen="shipment.incident",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id, "idioma": idioma},
    )


async def _procesar_shipment_returned(payload: dict):
    envio = await _obtener_envio(payload["envio_id"])
    cliente_id = envio.get("cliente_id") if envio else None
    canal, idioma = _resolver_canal(cliente_id, "email")
    mensaje = (
        f"Tu envío {payload['envio_id']} fue devuelto. Motivo: "
        f"{payload.get('notas') or 'no se especificó un motivo'}. "
        f"Si tienes dudas, contáctanos y con gusto te ayudamos."
    )
    registrar_notificacion(
        destinatario_tipo="cliente",
        canal=canal,
        mensaje=mensaje,
        evento_origen="shipment.returned",
        referencia={"envio_id": payload["envio_id"], "cliente_id": cliente_id, "idioma": idioma},
    )


async def _procesar_maintenance_alert(payload: dict):
    # Dirigido al gestor de flota, no a un cliente final — no aplica preferencia de canal.
    mensaje = (
        f"⚠ Alerta de mantenimiento — Vehículo {payload.get('vehiculo_id')}: "
        f"{payload.get('motivo')} (prioridad: {payload.get('prioridad')})."
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