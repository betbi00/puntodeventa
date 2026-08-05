"""Modelo y acceso a datos de bebidas (catálogo de precio fijo)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Bebida:
    id: int
    nombre: str
    precio: float
    activo: bool

    @staticmethod
    def from_row(row) -> "Bebida":
        return Bebida(id=row["id"], nombre=row["nombre"], precio=row["precio"], activo=bool(row["activo"]))


def listar(incluir_inactivos: bool = True) -> list[Bebida]:
    query = "SELECT * FROM bebidas"
    if not incluir_inactivos:
        query += " WHERE activo = 1"
    query += " ORDER BY nombre"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [Bebida.from_row(row) for row in rows]


def get_by_id(bebida_id: int) -> Optional[Bebida]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM bebidas WHERE id = ?", (bebida_id,)).fetchone()
    return Bebida.from_row(row) if row else None


def crear(nombre: str, precio: float) -> Bebida:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO bebidas (nombre, precio) VALUES (?, ?)", (nombre, precio)
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(bebida_id: int, nombre: str, precio: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bebidas SET nombre = ?, precio = ? WHERE id = ?", (nombre, precio, bebida_id)
        )


def set_activo(bebida_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE bebidas SET activo = ? WHERE id = ?", (1 if activo else 0, bebida_id))
