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

---

<!-- entrega-final -->

## Descripción

Genera notificaciones a partir de los eventos del sistema (en memoria) y guarda las preferencias de canal e idioma de cada cliente.

- **Puerto local:** 8007   ·   **Despliegue activo:** <https://logitrack-notification.onrender.com> (`/health` y `/metrics` públicos)
- **Imagen Docker:** `<usuario-dockerhub>/logitrack-notification`   ·   **Repositorio de CI/CD:** `LogiTrackSystem/pipelines`

## Variables de entorno

Copia `.env.example` como `.env` y completa los valores. El `.env` **no se sube** al repositorio.

| Variable | Para qué sirve |
|---|---|
| `RABBITMQ_URL` | URL AMQP del bus de eventos RabbitMQ (CloudAMQP en producción). Es un secreto. |
| `SHIPMENT_SERVICE_URL` | URL base de Shipment Service, sin barra final (en local `http://localhost:<puerto>`). |
| `INTERNAL_API_KEY` | Clave compartida entre el gateway y los servicios: exige la cabecera `X-Internal-Key` en todas las rutas salvo `/health` y `/metrics`. Vacía = sin restricción (solo local). Es un secreto. |

## Documentación de la API

- **Local** (sin `INTERNAL_API_KEY`): <http://localhost:8007/docs> (Swagger) y `http://localhost:8007/openapi.json`.
- **Producción:** el servicio solo atiende peticiones que llegan por el gateway (con `INTERNAL_API_KEY` activa su `/docs` no es público); la documentación de todas las rutas está en <https://logitrack-gateway.onrender.com/docs>.

## Base de datos

Este servicio no usa base de datos propia. Su estado vive en memoria.

## Pruebas

Con el entorno virtual activo y `pip install -r requirements-dev.txt`:

```
pytest tests/unit                    # 2 pruebas unitarias
pytest tests/integration             # 1 prueba de integración
pytest --cov=app --cov-report=term   # toda la suite con cobertura
```

| Prueba | Qué verifica |
|---|---|
| Unitaria 1 | `events._resolver_canal` |
| Unitaria 2 | `events._procesar_shipment_delivered` |
| Integración | preferencia por API → evento de entrega → notificación consultable |

Archivos: `tests/unit/` y `tests/integration/` (test_resolver_canal.py, test_envio_entregado.py, test_flujo_notificaciones.py). Cobertura de `app/` medida: **≈ 89 %**; en cada push y Pull Request GitHub Actions la recalcula y guarda `coverage.xml` como artefacto (`cobertura-notification`).

## Métricas y monitoreo

Expone `GET /metrics` (formato Prometheus: `http_requests_total` y `http_request_duration_*`). Prometheus y el dashboard de Grafana están en el repositorio `logitrack-monitoring`.

## CI/CD

- `.github/workflows/pr.yml`: en cada push (rama distinta de `main`) y en cada Pull Request a `main` ejecuta el CI reutilizable (lint, pruebas con cobertura, `docker build` y prueba de arranque).
- `.github/workflows/deploy.yml`: al fusionar en `main`, y solo con las pruebas en verde, publica la imagen en Docker Hub y despliega en Render (con verificación de `/health` y rollback manual).
- Detalle y estrategia de ramas: `CICD.md` en el repositorio `LogiTrackSystem/pipelines`.

