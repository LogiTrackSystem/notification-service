# Notification Service

Microservicio transversal de notificaciones. Escucha eventos de envío, incidencia y mantenimiento (`route.assigned`, `shipment.delivered`, `shipment.incident`, `shipment.returned`, `maintenance.alert`) y simula el envío de notificaciones a clientes y gestores de flota por el canal correspondiente (SMS, email, push).

Es el único microservicio del proyecto sin base de datos propia (así lo define el PDF de requerimientos). No hay integración real con proveedores de SMS/email/push ni con un sistema de preferencias de clientes (no existen en el modelo de datos del proyecto), así que el envío se simula: cada notificación generada se guarda en una lista en memoria del proceso (se pierde al reiniciar el servicio) para poder verificarla en las pruebas.

## Requisitos

- Python 3.11+
- RabbitMQ
- Shipment Service corriendo (se consulta por REST para obtener el `cliente_id` de un envío cuando el evento no lo trae)

## Setup

1. Copiar `.env.example` a `.env` (no requiere edición, no tiene secretos).
2. `python -m venv venv && venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. `uvicorn app.main:app --reload --port 8007`

## Endpoints

- `GET /notificaciones/` — lista las notificaciones simuladas más recientes (en memoria, no persistente).
- `GET /health` — healthcheck.

## Eventos

- **Consume:** `route.assigned`, `shipment.delivered`, `shipment.incident`, `shipment.returned`, `maintenance.alert`
- **Publica:** ninguno (es un consumidor puro)