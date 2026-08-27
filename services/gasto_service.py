"""Lógica de negocio de gastos del negocio (renta, agua, luz, insumos
comprados fuera del flujo de ventas, mantenimiento, etc.)."""
import datetime
from typing import Optional

from models import gasto as gasto_model
from models.gasto import Gasto

CATEGORIAS = ["renta", "agua", "luz", "insumos", "mantenimiento", "otro"]
CATEGORIA_ETIQUETAS = {
    "renta": "Renta",
    "agua": "Agua",
    "luz": "Luz",
    "insumos": "Insumos / compras",
    "mantenimiento": "Mantenimiento",
    "otro": "Otro",
}


class ValidationError(Exception):
    """Datos de entrada inválidos."""


def _validar(concepto: str, categoria: str, monto: float, fecha: str):
    if not concepto.strip():
        raise ValidationError("El concepto es obligatorio")
    if categoria not in CATEGORIAS:
        raise ValidationError(f"Categoría inválida: {categoria}")
    if monto <= 0:
        raise ValidationError("El monto debe ser mayor a cero")
    try:
        datetime.date.fromisoformat(fecha)
    except ValueError:
        raise ValidationError("La fecha debe tener formato YYYY-MM-DD") from None


def crear_gasto(
    concepto: str, categoria: str, monto: float, fecha: str, usuario_id: int, notas: Optional[str] = None,
) -> Gasto:
    concepto = concepto.strip()
    _validar(concepto, categoria, monto, fecha)
    return gasto_model.crear(concepto, categoria, monto, fecha, usuario_id, (notas or "").strip() or None)


def actualizar_gasto(
    gasto_id: int, concepto: str, categoria: str, monto: float, fecha: str, notas: Optional[str] = None,
) -> None:
    concepto = concepto.strip()
    _validar(concepto, categoria, monto, fecha)
    gasto_model.actualizar(gasto_id, concepto, categoria, monto, fecha, (notas or "").strip() or None)


def eliminar_gasto(gasto_id: int) -> None:
    gasto_model.eliminar(gasto_id)


def listar_gastos(desde: Optional[str] = None, hasta: Optional[str] = None, limite: Optional[int] = None) -> list[Gasto]:
    return gasto_model.listar(desde=desde, hasta=hasta, limite=limite)
