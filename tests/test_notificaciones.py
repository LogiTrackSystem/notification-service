"""Mensajes que se generan por cada evento, canal según preferencias y API de consulta."""
import asyncio
import json

import pytest

from app import events
from app.preferencias import configurar_preferencia
from app.store import listar_notificaciones

ENVIO = "11111111-1111-1111-1111-111111111111"
CLIENTE = "22222222-2222-2222-2222-222222222222"


def correr(corutina):
    return asyncio.run(corutina)


# ---------- formato de la hora estimada ----------

def test_eta_se_muestra_en_hora_de_colombia():
    assert events._formatear_eta("2026-10-21T17:00:00+00:00") == "21/10/2026 12:00"


def test_eta_sin_zona_horaria_se_toma_como_utc():
    assert events._formatear_eta("2026-10-21T17:00:00") == "21/10/2026 12:00"


def test_eta_invalida_o_ausente_no_rompe():
    assert events._formatear_eta("manana") is None
    assert events._formatear_eta(None) is None


# ---------- canal y preferencias ----------

def test_sin_cliente_se_usa_el_canal_por_defecto():
    assert events._resolver_canal(None, "sms") == ("sms", "es")


def test_el_canal_preferido_del_cliente_reemplaza_al_de_por_defecto():
    configurar_preferencia(CLIENTE, "en", "email")
    assert events._resolver_canal(CLIENTE, "push") == ("email", "en")


def test_cliente_sin_preferencia_usa_el_canal_por_defecto():
    assert events._resolver_canal(CLIENTE, "push") == ("push", "es")


# ---------- eventos ----------

def test_ruta_asignada_incluye_codigo_vehiculo_conductor_y_eta(envios):
    envios[ENVIO] = {"cliente_id": CLIENTE, "codigo_envio": "ENV-00000007"}
    correr(events._procesar_route_assigned({
        "envio_id": ENVIO, "placa": "ABC123", "conductor_nombre": "Ana",
        "hora_estimada_llegada": "2026-10-21T17:00:00+00:00", "ruta_id": "r1"}))
    n = listar_notificaciones()[0]
    assert n["evento_origen"] == "route.assigned" and n["canal"] == "push" and n["destinatario_tipo"] == "cliente"
    assert "ENV-00000007" in n["mensaje"] and "ABC123" in n["mensaje"] and "Ana" in n["mensaje"]
    assert "21/10/2026 12:00" in n["mensaje"]
    assert n["referencia"]["cliente_id"] == CLIENTE and n["referencia"]["ruta_id"] == "r1"


def test_si_shipment_no_responde_se_usa_el_id_del_envio_como_codigo(envios):
    correr(events._procesar_route_assigned({"envio_id": ENVIO}))
    n = listar_notificaciones()[0]
    assert ENVIO in n["mensaje"] and n["referencia"]["cliente_id"] is None


def test_viaje_iniciado_respeta_la_preferencia_de_canal(envios):
    envios[ENVIO] = {"cliente_id": CLIENTE, "codigo_envio": "ENV-1"}
    configurar_preferencia(CLIENTE, "es", "sms")
    correr(events._procesar_trip_started({"envio_id": ENVIO, "placa": "XYZ987"}))
    n = listar_notificaciones()[0]
    assert n["canal"] == "sms" and "en camino" in n["mensaje"] and "XYZ987" in n["mensaje"]


def test_entrega_va_por_email_y_nombra_al_receptor(envios):
    correr(events._procesar_shipment_delivered({"envio_id": ENVIO, "nombre_receptor": "Luis", "entregado_en": "hoy"}))
    n = listar_notificaciones()[0]
    assert n["canal"] == "email" and "Luis" in n["mensaje"] and "entregado" in n["mensaje"]


def test_incidencia_va_por_sms_y_sin_notas_usa_un_texto_generico(envios):
    correr(events._procesar_shipment_incident({"envio_id": ENVIO}))
    n = listar_notificaciones()[0]
    assert n["canal"] == "sms" and "estamos revisando los detalles" in n["mensaje"]


def test_devolucion_incluye_el_motivo(envios):
    correr(events._procesar_shipment_returned({"envio_id": ENVIO, "notas": "Dirección errónea"}))
    n = listar_notificaciones()[0]
    assert n["canal"] == "email" and "Dirección errónea" in n["mensaje"]


def test_alerta_de_mantenimiento_va_al_gestor_y_no_usa_preferencias(envios):
    correr(events._procesar_maintenance_alert({"vehiculo_id": "v1", "motivo": "temperatura_motor", "prioridad": "critica"}))
    n = listar_notificaciones()[0]
    assert n["destinatario_tipo"] == "gestor_flota" and n["canal"] == "push"
    assert "temperatura_motor" in n["mensaje"] and "critica" in n["mensaje"]


# ---------- consumo de mensajes ----------

class MensajeFalso:
    def __init__(self, clave, payload):
        self.routing_key = clave
        self.body = json.dumps(payload).encode()

    def process(self):
        class Contexto:
            async def __aenter__(self_):
                return None

            async def __aexit__(self_, *a):
                return False

        return Contexto()


def test_el_consumidor_enruta_cada_evento_a_su_manejador(envios):
    correr(events._on_message(MensajeFalso("shipment.delivered", {"envio_id": ENVIO, "nombre_receptor": "Luis"})))
    assert listar_notificaciones()[0]["evento_origen"] == "shipment.delivered"


def test_un_evento_desconocido_se_ignora(envios):
    correr(events._on_message(MensajeFalso("otra.cosa", {"envio_id": ENVIO})))
    assert listar_notificaciones() == []


def test_un_evento_malformado_no_tumba_el_consumidor(envios):
    correr(events._on_message(MensajeFalso("shipment.delivered", {})))  # sin envio_id: KeyError controlado
    assert listar_notificaciones() == []


@pytest.mark.parametrize("clave", events.ROUTING_KEYS)
def test_todas_las_claves_suscritas_tienen_manejador(clave):
    assert clave in events._HANDLERS


# ---------- API ----------

def test_listar_notificaciones_de_la_mas_reciente_a_la_mas_antigua(api, envios):
    correr(events._procesar_shipment_returned({"envio_id": "a"}))
    correr(events._procesar_shipment_incident({"envio_id": "b"}))
    r = api.get("/notificaciones/")
    assert r.status_code == 200
    assert [n["evento_origen"] for n in r.json()] == ["shipment.incident", "shipment.returned"]


def test_limite_de_la_lista(api, envios):
    for i in range(5):
        correr(events._procesar_shipment_incident({"envio_id": str(i)}))
    assert len(api.get("/notificaciones/?limite=2").json()) == 2
    assert api.get("/notificaciones/?limite=201").status_code == 422


def test_preferencias_por_defecto_y_guardado(api):
    assert api.get(f"/preferencias/{CLIENTE}").json() == {"idioma": "es", "canal_preferido": None}
    r = api.post(f"/preferencias/{CLIENTE}", json={"idioma": "en", "canal_preferido": "sms"})
    assert r.status_code == 200
    assert api.get(f"/preferencias/{CLIENTE}").json() == {"idioma": "en", "canal_preferido": "sms"}


def test_preferencias_rechaza_valores_invalidos(api):
    assert api.post(f"/preferencias/{CLIENTE}", json={"idioma": "fr"}).status_code == 422
    assert api.post(f"/preferencias/{CLIENTE}", json={"canal_preferido": "paloma"}).status_code == 422
    assert api.get(f"/preferencias/{CLIENTE}").json()["idioma"] == "es"  # nada se guardó
