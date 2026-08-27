"""Modelo y acceso a datos de ventas: encabezado, detalle de productos y
los insumos elegidos en cada uno (ingredientes de crepa/waffle, extras de
bebida). Se usa para tickets (Fase 4) y reportes (Fase 6)."""
from dataclasses import dataclass, field
from typing import Optional

from db.connection import get_connection


@dataclass
class InsumoDetalle:
    insumo_id: int
    nombre_insumo: str
    precio_extra: float
    cantidad_usada: float


@dataclass
class DetalleVenta:
    id: int
    tipo_producto: str
    nombre_producto: str
    precio_unitario: float
    cantidad: int
    subtotal_item: float
    insumos: list = field(default_factory=list)  # list[InsumoDetalle]


@dataclass
class Venta:
    id: int
    fecha_hora: str
    usuario_id: int
    subtotal: float
    descuento_pct: float
    descuento_monto: float
    total: float
    metodo_pago: str
    mp_payment_id: Optional[str]
    mp_status: Optional[str]
    ticket_impreso: bool
    estado: str
    detalles: list = field(default_factory=list)  # list[DetalleVenta], solo en get_completa


def _venta_from_row(row) -> Venta:
    return Venta(
        id=row["id"], fecha_hora=row["fecha_hora"], usuario_id=row["usuario_id"],
        subtotal=row["subtotal"], descuento_pct=row["descuento_pct"], descuento_monto=row["descuento_monto"],
        total=row["total"], metodo_pago=row["metodo_pago"], mp_payment_id=row["mp_payment_id"],
        mp_status=row["mp_status"], ticket_impreso=bool(row["ticket_impreso"]), estado=row["estado"],
    )


def get_by_id(venta_id: int) -> Optional[Venta]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
    return _venta_from_row(row) if row else None


def get_completa(venta_id: int) -> Optional[Venta]:
    """Trae la venta junto con el detalle de productos y los insumos
    elegidos en cada uno."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,)).fetchone()
        if not row:
            return None
        venta = _venta_from_row(row)

        detalle_rows = conn.execute(
            "SELECT * FROM detalle_venta WHERE venta_id = ? ORDER BY id", (venta_id,)
        ).fetchall()
        for drow in detalle_rows:
            insumo_rows = conn.execute(
                "SELECT * FROM detalle_venta_insumos WHERE detalle_venta_id = ? ORDER BY id", (drow["id"],)
            ).fetchall()
            insumos = [
                InsumoDetalle(
                    insumo_id=irow["insumo_id"], nombre_insumo=irow["nombre_insumo"],
                    precio_extra=irow["precio_extra"], cantidad_usada=irow["cantidad_usada"],
                )
                for irow in insumo_rows
            ]
            venta.detalles.append(
                DetalleVenta(
                    id=drow["id"], tipo_producto=drow["tipo_producto"], nombre_producto=drow["nombre_producto"],
                    precio_unitario=drow["precio_unitario"], cantidad=drow["cantidad"],
                    subtotal_item=drow["subtotal_item"], insumos=insumos,
                )
            )
    return venta


def marcar_ticket_impreso(venta_id: int, impreso: bool = True) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE ventas SET ticket_impreso = ? WHERE id = ?", (1 if impreso else 0, venta_id))


def listar_recientes(limite: int = 20) -> list[Venta]:
    """Para poder reimprimir una venta reciente (Fase 4) antes de que exista
    el módulo completo de reportes (Fase 6)."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM ventas ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [_venta_from_row(row) for row in rows]
