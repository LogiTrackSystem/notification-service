"""/health y la clave interna (INTERNAL_API_KEY): el servicio solo atiende lo que llega por el gateway."""
from fastapi.testclient import TestClient

from app.main import app

CLIENTE = TestClient(app)
RUTA = "/ruta-que-no-existe"


def test_health_devuelve_la_version_de_la_imagen(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc1234")
    r = CLIENTE.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "notification-service", "version": "abc1234"}


def test_health_sin_version_indica_dev(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert CLIENTE.get("/health").json()["version"] == "dev"


def test_sin_clave_configurada_no_se_exige_nada(monkeypatch):
    monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
    assert CLIENTE.get(RUTA).status_code == 404


def test_con_clave_configurada_se_rechaza_si_falta_o_es_incorrecta(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "clave-de-prueba-123")
    sin = CLIENTE.get(RUTA)
    assert sin.status_code == 403
    assert sin.json()["detail"]["codigo"] == "ACCESO_DIRECTO_NO_PERMITIDO"
    assert CLIENTE.get(RUTA, headers={"X-Internal-Key": "otra"}).status_code == 403


def test_con_la_clave_correcta_pasa(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "clave-de-prueba-123")
    assert CLIENTE.get(RUTA, headers={"X-Internal-Key": "clave-de-prueba-123"}).status_code == 404


def test_health_queda_abierto_aunque_haya_clave(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_KEY", "clave-de-prueba-123")
    assert CLIENTE.get("/health").status_code == 200
