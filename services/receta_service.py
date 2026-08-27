"""Lógica de negocio de recetas: copiar la imagen del paso a paso al
proyecto (para que no se rompa si el archivo original se mueve o se
borra) y CRUD de recetas."""
import shutil
import uuid
from pathlib import Path
from typing import Optional

from config import ASSETS_DIR
from models import receta as receta_model
from models.receta import Receta

IMAGENES_DIR = ASSETS_DIR / "recetas_imagenes"


class ValidationError(Exception):
    """Datos de entrada inválidos."""


def _copiar_imagen(ruta_origen: str) -> str:
    """Copia la imagen elegida a assets/recetas_imagenes con un nombre
    único, para que la receta no dependa de que el archivo original siga
    existiendo en su ubicación original (ej. una carpeta de Descargas)."""
    origen = Path(ruta_origen)
    IMAGENES_DIR.mkdir(parents=True, exist_ok=True)
    destino = IMAGENES_DIR / f"{uuid.uuid4().hex}{origen.suffix.lower()}"
    shutil.copyfile(origen, destino)
    return str(destino)


def crear_receta(
    nombre_producto: str, creado_por: int, imagen_pasos: Optional[str] = None,
    ingredientes: Optional[str] = None, pasos: Optional[str] = None,
) -> Receta:
    nombre_producto = nombre_producto.strip()
    if not nombre_producto:
        raise ValidationError("El nombre del producto es obligatorio")
    if not imagen_pasos:
        raise ValidationError("La imagen del paso a paso es obligatoria")

    imagen_pasos_path = _copiar_imagen(imagen_pasos)

    return receta_model.crear(
        nombre_producto, imagen_pasos_path,
        (ingredientes or "").strip() or None, (pasos or "").strip() or None, creado_por,
    )


def actualizar_receta(
    receta_id: int, nombre_producto: str, imagen_pasos: Optional[str] = None,
    ingredientes: Optional[str] = None, pasos: Optional[str] = None,
) -> None:
    nombre_producto = nombre_producto.strip()
    if not nombre_producto:
        raise ValidationError("El nombre del producto es obligatorio")

    receta_actual = receta_model.get_by_id(receta_id)
    if not receta_actual:
        raise ValidationError("La receta no existe")

    # Si no se eligió una imagen nueva, se conserva la que ya tenía.
    imagen_pasos_path = _copiar_imagen(imagen_pasos) if imagen_pasos else receta_actual.imagen_pasos_path
    if not imagen_pasos_path:
        raise ValidationError("La imagen del paso a paso es obligatoria")

    receta_model.actualizar(
        receta_id, nombre_producto, imagen_pasos_path,
        (ingredientes or "").strip() or None, (pasos or "").strip() or None,
    )


def Quitar_receta(receta_id: int) -> None:
    receta_model.eliminar(receta_id)


def listar_recetas() -> list[Receta]:
    return receta_model.listar()
