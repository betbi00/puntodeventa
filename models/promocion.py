"""Modelo y acceso a datos de promociones con nombre (ej. "Promoción día
del niño"). No se eliminan, solo se desactivan: las ventas ya hechas con
una promoción deben conservar la referencia para los reportes."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Promocion:
    id: int
    nombre: str
    porcentaje: float
    activo: bool
    fecha_creacion: str

    @staticmethod
    def from_row(row) -> "Promocion":
        return Promocion(
            id=row["id"],
            nombre=row["nombre"],
            porcentaje=row["porcentaje"],
            activo=bool(row["activo"]),
            fecha_creacion=row["fecha_creacion"],
        )


def listar(incluir_inactivas: bool = True) -> list[Promocion]:
    query = "SELECT * FROM promociones"
    if not incluir_inactivas:
        query += " WHERE activo = 1"
    query += " ORDER BY fecha_creacion DESC"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [Promocion.from_row(r) for r in rows]


def get_by_id(promocion_id: int) -> Optional[Promocion]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM promociones WHERE id = ?", (promocion_id,)).fetchone()
    return Promocion.from_row(row) if row else None


def crear(nombre: str, porcentaje: float) -> Promocion:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO promociones (nombre, porcentaje) VALUES (?, ?)", (nombre, porcentaje)
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(promocion_id: int, nombre: str, porcentaje: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE promociones SET nombre = ?, porcentaje = ? WHERE id = ?",
            (nombre, porcentaje, promocion_id),
        )


def set_activo(promocion_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE promociones SET activo = ? WHERE id = ?", (1 if activo else 0, promocion_id))
