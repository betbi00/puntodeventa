"""Modelo y acceso a datos de bebidas (catálogo de precio fijo)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Bebida:
    id: int
    nombre: str
    precio: float
    stock_actual: float
    stock_minimo: float
    activo: bool

    @staticmethod
    def from_row(row) -> "Bebida":
        return Bebida(
            id=row["id"], nombre=row["nombre"], precio=row["precio"],
            stock_actual=row["stock_actual"], stock_minimo=row["stock_minimo"],
            activo=bool(row["activo"]),
        )

    @property
    def bajo_stock_minimo(self) -> bool:
        return self.stock_actual < self.stock_minimo


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


def crear(nombre: str, precio: float, stock_inicial: float = 0, stock_minimo: float = 0) -> Bebida:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO bebidas (nombre, precio, stock_actual, stock_minimo) VALUES (?, ?, ?, ?)",
            (nombre, precio, stock_inicial, stock_minimo),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(bebida_id: int, nombre: str, precio: float, stock_minimo: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bebidas SET nombre = ?, precio = ?, stock_minimo = ? WHERE id = ?",
            (nombre, precio, stock_minimo, bebida_id),
        )


def set_activo(bebida_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE bebidas SET activo = ? WHERE id = ?", (1 if activo else 0, bebida_id))
