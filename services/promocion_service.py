"""Lógica de negocio de promociones con nombre (ej. "Promoción día del
niño (10%)") dadas de alta por el administrador desde el Dashboard, que
aparecen como botón de acceso rápido al cobrar."""
from models import promocion as promocion_model
from models.promocion import Promocion


class ValidationError(Exception):
    """Datos de entrada inválidos."""


def _validar(nombre: str, porcentaje: float):
    if not nombre.strip():
        raise ValidationError("El nombre de la promoción es obligatorio")
    if not (0 < porcentaje <= 100):
        raise ValidationError("El porcentaje debe ser mayor a 0 y menor o igual a 100")


def crear_promocion(nombre: str, porcentaje: float) -> Promocion:
    nombre = nombre.strip()
    _validar(nombre, porcentaje)
    return promocion_model.crear(nombre, porcentaje)


def actualizar_promocion(promocion_id: int, nombre: str, porcentaje: float) -> None:
    nombre = nombre.strip()
    _validar(nombre, porcentaje)
    promocion_model.actualizar(promocion_id, nombre, porcentaje)


def set_activo_promocion(promocion_id: int, activo: bool) -> None:
    promocion_model.set_activo(promocion_id, activo)


def listar_promociones(incluir_inactivas: bool = True) -> list[Promocion]:
    return promocion_model.listar(incluir_inactivas=incluir_inactivas)
