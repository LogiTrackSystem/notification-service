from typing import Any, Dict
from pydantic import BaseModel


class NotificacionLeer(BaseModel):
    id: str
    destinatario_tipo: str
    canal: str
    mensaje: str
    evento_origen: str
    referencia: Dict[str, Any]
    enviado_en: str