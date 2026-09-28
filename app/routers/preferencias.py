from fastapi import APIRouter, HTTPException

from ..preferencias import configurar_preferencia, obtener_preferencia, IDIOMAS_VALIDOS, CANALES_VALIDOS
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/preferencias", tags=["Preferencias"])


class PreferenciaCrear(BaseModel):
    idioma: str = "es"
    canal_preferido: Optional[str] = None


@router.post("/{cliente_id}")
def establecer_preferencia(cliente_id: str, payload: PreferenciaCrear):
    if payload.idioma not in IDIOMAS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"idioma debe ser uno de: {', '.join(IDIOMAS_VALIDOS)}")
    if payload.canal_preferido and payload.canal_preferido not in CANALES_VALIDOS:
        raise HTTPException(status_code=422, detail=f"canal_preferido debe ser uno de: {', '.join(CANALES_VALIDOS)}")
    return configurar_preferencia(cliente_id, payload.idioma, payload.canal_preferido)


@router.get("/{cliente_id}")
def leer_preferencia(cliente_id: str):
    return obtener_preferencia(cliente_id)