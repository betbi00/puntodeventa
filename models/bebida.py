"""Modelo y acceso a datos de bebidas (catálogo de precio fijo)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection

# Qué extra se le ofrece al cliente al agregar la bebida al carrito:
# 'boba_perlas' (varias a la vez) o 'pulpa' (una sola). None = sin extras.
TIPOS_EXTRA_VALIDOS = ("boba_perlas", "pulpa")


@dataclass
class Bebida:
    id: int
    nombre: str
    precio: float
    tipo_extra: Optional[str]
    stock_actual: float
    stock_minimo: float
    activo: bool

    @staticmethod
    def from_row(row) -> "Bebida":
        return Bebida(
            id=row["id"], nombre=row["nombre"], precio=row["precio"],
            tipo_extra=row["tipo_extra"],
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


def crear(
    nombre: str, precio: float, stock_inicial: float = 0, stock_minimo: float = 0,
    tipo_extra: Optional[str] = None,
) -> Bebida:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO bebidas (nombre, precio, tipo_extra, stock_actual, stock_minimo) VALUES (?, ?, ?, ?, ?)",
            (nombre, precio, tipo_extra, stock_inicial, stock_minimo),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(
    bebida_id: int, nombre: str, precio: float, stock_minimo: float, tipo_extra: Optional[str] = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bebidas SET nombre = ?, precio = ?, stock_minimo = ?, tipo_extra = ? WHERE id = ?",
            (nombre, precio, stock_minimo, tipo_extra, bebida_id),
        )


def set_activo(bebida_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE bebidas SET activo = ? WHERE id = ?", (1 if activo else 0, bebida_id))


def tiene_historial(bebida_id: int) -> bool:
    """True si alguna vez se vendió (detalle_venta) o tiene algún
    movimiento de stock (movimientos_inventario) — en ese caso no se
    puede eliminar de verdad, solo desactivar."""
    with get_connection() as conn:
        en_ventas = conn.execute(
            "SELECT 1 FROM detalle_venta WHERE bebida_id = ? LIMIT 1", (bebida_id,)
        ).fetchone()
        if en_ventas:
            return True
        en_movimientos = conn.execute(
            "SELECT 1 FROM movimientos_inventario WHERE bebida_id = ? LIMIT 1", (bebida_id,)
        ).fetchone()
    return en_movimientos is not None


def eliminar(bebida_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM bebidas WHERE id = ?", (bebida_id,))
