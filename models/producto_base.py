"""Modelo y acceso a datos de productos base (Crepa, Waffle)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class ProductoBase:
    id: int
    nombre: str
    precio_base: float
    activo: bool

    @staticmethod
    def from_row(row) -> "ProductoBase":
        return ProductoBase(
            id=row["id"], nombre=row["nombre"], precio_base=row["precio_base"], activo=bool(row["activo"])
        )


def listar(incluir_inactivos: bool = True) -> list[ProductoBase]:
    query = "SELECT * FROM productos_base"
    if not incluir_inactivos:
        query += " WHERE activo = 1"
    query += " ORDER BY nombre"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [ProductoBase.from_row(row) for row in rows]


def get_by_id(producto_id: int) -> Optional[ProductoBase]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM productos_base WHERE id = ?", (producto_id,)).fetchone()
    return ProductoBase.from_row(row) if row else None


def existe_nombre(nombre: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM productos_base WHERE nombre = ?", (nombre,)
        ).fetchone()
    return row is not None


def crear(nombre: str, precio_base: float) -> ProductoBase:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO productos_base (nombre, precio_base) VALUES (?, ?)", (nombre, precio_base)
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(producto_id: int, nombre: str, precio_base: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE productos_base SET nombre = ?, precio_base = ? WHERE id = ?",
            (nombre, precio_base, producto_id),
        )


def set_activo(producto_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE productos_base SET activo = ? WHERE id = ?", (1 if activo else 0, producto_id)
        )
