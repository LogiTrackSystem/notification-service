"""Registro en memoria de preferencias de notificación por cliente"""

IDIOMAS_VALIDOS = {"es", "en"}
CANALES_VALIDOS = {"sms", "email", "push"}

_preferencias: dict[str, dict] = {}


def configurar_preferencia(cliente_id: str, idioma: str = "es", canal_preferido: str | None = None):
    _preferencias[cliente_id] = {"idioma": idioma, "canal_preferido": canal_preferido}
    return _preferencias[cliente_id]


def obtener_preferencia(cliente_id: str) -> dict:
    return _preferencias.get(cliente_id, {"idioma": "es", "canal_preferido": None})