import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

_notificaciones: List[Dict[str, Any]] = []


def registrar_notificacion(destinatario_tipo: str, canal: str, mensaje: str, evento_origen: str, referencia: dict) -> dict:
    notificacion = {
        "id": str(uuid.uuid4()),
        "destinatario_tipo": destinatario_tipo,
        "canal": canal,
        "mensaje": mensaje,
        "evento_origen": evento_origen,
        "referencia": referencia,
        "enviado_en": datetime.now(timezone.utc).isoformat(),
    }
    _notificaciones.insert(0, notificacion)
    return notificacion


def listar_notificaciones(limite: int = 50) -> List[Dict[str, Any]]:
    return _notificaciones[:limite]