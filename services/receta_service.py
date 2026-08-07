"""Lógica de negocio de recetas: extraer el video_id de una URL de
YouTube, intentar descargar su miniatura automáticamente (con opción de
subir una imagen manual), y CRUD de recetas."""
import re
from pathlib import Path
from typing import Optional

import requests

from config import ASSETS_DIR
from models import receta as receta_model
from models.receta import Receta

THUMBNAILS_DIR = ASSETS_DIR / "recetas_thumbnails"

# Cubre watch?v=, youtu.be/, embed/ y shorts/, con o sin parámetros extra (&list=, &t=, etc.)
PATRONES_YOUTUBE = [
    r"(?:youtube\.com/watch\?v=|youtube\.com/embed/|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
]


class ValidationError(Exception):
    """Datos de entrada inválidos."""


def extraer_video_id(url: str) -> Optional[str]:
    for patron in PATRONES_YOUTUBE:
        match = re.search(patron, url)
        if match:
            return match.group(1)
    return None


def _descargar_miniatura_automatica(video_id: str) -> Optional[str]:
    """Intenta descargar la miniatura pública de YouTube. Funciona para
    videos no listados (no requiere que el video sea público/buscable);
    los verdaderamente privados fallarán y la miniatura queda en None para
    que el administrador suba una manualmente."""
    url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # YouTube devuelve una imagen placeholder gris muy chica cuando el
        # video no existe o no tiene miniatura pública disponible.
        if len(resp.content) < 2000:
            return None
    except requests.RequestException:
        return None

    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = THUMBNAILS_DIR / f"{video_id}.jpg"
    ruta.write_bytes(resp.content)
    return str(ruta)


def crear_receta(
    nombre_producto: str, video_url: str, creado_por: int, miniatura_manual: Optional[str] = None,
    ingredientes: Optional[str] = None, pasos: Optional[str] = None,
) -> Receta:
    nombre_producto = nombre_producto.strip()
    video_url = video_url.strip()
    if not nombre_producto:
        raise ValidationError("El nombre del producto es obligatorio")
    if not video_url:
        raise ValidationError("El link del video es obligatorio")

    video_id = extraer_video_id(video_url)
    miniatura_path = miniatura_manual or (_descargar_miniatura_automatica(video_id) if video_id else None)

    return receta_model.crear(
        nombre_producto, video_url, video_id, miniatura_path,
        (ingredientes or "").strip() or None, (pasos or "").strip() or None, creado_por,
    )


def actualizar_receta(
    receta_id: int, nombre_producto: str, video_url: str, miniatura_manual: Optional[str] = None,
    ingredientes: Optional[str] = None, pasos: Optional[str] = None,
) -> None:
    nombre_producto = nombre_producto.strip()
    video_url = video_url.strip()
    if not nombre_producto:
        raise ValidationError("El nombre del producto es obligatorio")
    if not video_url:
        raise ValidationError("El link del video es obligatorio")

    receta_actual = receta_model.get_by_id(receta_id)
    if not receta_actual:
        raise ValidationError("La receta no existe")

    video_id = extraer_video_id(video_url)

    if miniatura_manual:
        miniatura_path = miniatura_manual
    elif video_id != receta_actual.video_id:
        # Cambió el video: intentar descargar la miniatura del nuevo.
        miniatura_path = _descargar_miniatura_automatica(video_id) if video_id else None
    else:
        # Mismo video: conservar la miniatura que ya tenía, para no
        # perderla si la descarga automática falla por falta de internet
        # en una edición que no tenía nada que ver con el video.
        miniatura_path = receta_actual.miniatura_path

    receta_model.actualizar(
        receta_id, nombre_producto, video_url, video_id, miniatura_path,
        (ingredientes or "").strip() or None, (pasos or "").strip() or None,
    )


def eliminar_receta(receta_id: int) -> None:
    receta_model.eliminar(receta_id)


def listar_recetas() -> list[Receta]:
    return receta_model.listar()
