from typing import List

from fastapi import APIRouter, Query

from ..schemas import NotificacionLeer
from ..store import listar_notificaciones

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("/", response_model=List[NotificacionLeer])
def listar(limite: int = Query(50, le=200)):
    return listar_notificaciones(limite)