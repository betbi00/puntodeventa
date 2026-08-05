"""Modelo y acceso a datos de movimientos de inventario (bitácora de stock)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection

TIPOS_VALIDOS = ("entrada", "ajuste", "venta")


@dataclass
class MovimientoInventario:
    id: int
    insumo_id: int
    tipo: str
    cantidad: float
    stock_resultante: float
    motivo: Optional[str]
    usuario_id: int
    referencia_venta_id: Optional[int]
    fecha_hora: str

    @staticmethod
    def from_row(row) -> "MovimientoInventario":
        return MovimientoInventario(
            id=row["id"],
            insumo_id=row["insumo_id"],
            tipo=row["tipo"],
            cantidad=row["cantidad"],
            stock_resultante=row["stock_resultante"],
            motivo=row["motivo"],
            usuario_id=row["usuario_id"],
            referencia_venta_id=row["referencia_venta_id"],
            fecha_hora=row["fecha_hora"],
        )


def crear(
    conn, insumo_id: int, tipo: str, cantidad: float, stock_resultante: float,
    usuario_id: int, motivo: Optional[str] = None, referencia_venta_id: Optional[int] = None,
) -> None:
    """Recibe una conexión abierta para poder insertarse en la misma
    transacción que el UPDATE de stock_actual en insumos."""
    conn.execute(
        """INSERT INTO movimientos_inventario
           (insumo_id, tipo, cantidad, stock_resultante, motivo, usuario_id, referencia_venta_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (insumo_id, tipo, cantidad, stock_resultante, motivo, usuario_id, referencia_venta_id),
    )


def listar_por_insumo(insumo_id: int) -> list[MovimientoInventario]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM movimientos_inventario WHERE insumo_id = ? ORDER BY fecha_hora DESC",
            (insumo_id,),
        ).fetchall()
    return [MovimientoInventario.from_row(row) for row in rows]


def listar(desde: Optional[str] = None, hasta: Optional[str] = None) -> list[MovimientoInventario]:
    """Para el reporte de movimientos (Fase 6). desde/hasta en formato 'YYYY-MM-DD'."""
    query = "SELECT * FROM movimientos_inventario"
    condiciones = []
    params = []
    if desde:
        condiciones.append("fecha_hora >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("fecha_hora <= ?")
        params.append(hasta + " 23:59:59")
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY fecha_hora DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [MovimientoInventario.from_row(row) for row in rows]
