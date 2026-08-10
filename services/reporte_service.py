"""Consultas de reportes / "minería de datos" para el panel de
administrador. Todas reciben un rango de fechas inclusive en formato
'YYYY-MM-DD' y solo consideran ventas con estado='completada'."""
from db.connection import get_connection


def resumen_ventas(desde: str, hasta: str) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT
                   COUNT(*) AS num_ventas,
                   COALESCE(SUM(total), 0) AS ingresos_totales,
                   COALESCE(SUM(descuento_monto), 0) AS descuento_total,
                   COALESCE(SUM(CASE WHEN metodo_pago = 'efectivo' THEN total ELSE 0 END), 0) AS ingresos_efectivo,
                   COALESCE(SUM(CASE WHEN metodo_pago = 'tarjeta' THEN total ELSE 0 END), 0) AS ingresos_tarjeta
               FROM ventas
               WHERE estado = 'completada' AND date(fecha_hora) BETWEEN ? AND ?""",
            (desde, hasta),
        ).fetchone()

    num_ventas = row["num_ventas"]
    ingresos_totales = row["ingresos_totales"]
    return {
        "num_ventas": num_ventas,
        "ingresos_totales": ingresos_totales,
        "ticket_promedio": (ingresos_totales / num_ventas) if num_ventas else 0,
        "descuento_total": row["descuento_total"],
        "ingresos_efectivo": row["ingresos_efectivo"],
        "ingresos_tarjeta": row["ingresos_tarjeta"],
    }


def ventas_por_dia(desde: str, hasta: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT date(fecha_hora) AS dia, COUNT(*) AS num_ventas, SUM(total) AS ingresos
               FROM ventas
               WHERE estado = 'completada' AND date(fecha_hora) BETWEEN ? AND ?
               GROUP BY dia
               ORDER BY dia""",
            (desde, hasta),
        ).fetchall()
    return [{"dia": r["dia"], "num_ventas": r["num_ventas"], "ingresos": r["ingresos"]} for r in rows]


def productos_mas_vendidos(desde: str, hasta: str, limite: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT dv.nombre_producto AS nombre, SUM(dv.cantidad) AS cantidad, SUM(dv.subtotal_item) AS ingresos
               FROM detalle_venta dv
               JOIN ventas v ON v.id = dv.venta_id
               WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
               GROUP BY dv.nombre_producto
               ORDER BY cantidad DESC
               LIMIT ?""",
            (desde, hasta, limite),
        ).fetchall()
    return [{"nombre": r["nombre"], "cantidad": r["cantidad"], "ingresos": r["ingresos"]} for r in rows]


def ventas_por_empleado(desde: str, hasta: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT u.nombre AS nombre, COUNT(*) AS num_ventas, SUM(v.total) AS ingresos,
                      COALESCE(SUM(v.descuento_monto), 0) AS descuento_total
               FROM ventas v
               JOIN usuarios u ON u.id = v.usuario_id
               WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
               GROUP BY v.usuario_id
               ORDER BY ingresos DESC""",
            (desde, hasta),
        ).fetchall()
    return [
        {
            "nombre": r["nombre"], "num_ventas": r["num_ventas"], "ingresos": r["ingresos"],
            "descuento_total": r["descuento_total"],
        }
        for r in rows
    ]


def descuentos_aplicados(desde: str, hasta: str) -> list[dict]:
    """Una fila por cada venta con descuento (>0) dentro del rango: quién
    la cobró, cuánto fue el descuento y en qué día — a diferencia de
    ventas_por_empleado (que solo trae el acumulado), esto es el detalle
    evento por evento que permite revisar cada descuento aplicado."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT v.id AS venta_id, date(v.fecha_hora) AS dia, u.nombre AS empleado,
                      v.descuento_pct, v.descuento_monto, p.nombre AS promocion
               FROM ventas v
               JOIN usuarios u ON u.id = v.usuario_id
               LEFT JOIN promociones p ON p.id = v.promocion_id
               WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
                     AND v.descuento_monto > 0
               ORDER BY v.fecha_hora""",
            (desde, hasta),
        ).fetchall()
    return [
        {
            "venta_id": r["venta_id"], "dia": r["dia"], "empleado": r["empleado"],
            "descuento_pct": r["descuento_pct"], "descuento_monto": r["descuento_monto"],
            "promocion": r["promocion"],
        }
        for r in rows
    ]


def consumo_insumos(desde: str, hasta: str, tipos: list[str] = None) -> list[dict]:
    """Consumo total de insumos (ingredientes, y/o boba/perlas explosivas)
    usados en ventas dentro del rango. `tipos` filtra por insumos.tipo
    (ej. ['boba', 'perla_explosiva'] para el control de esos dos)."""
    params = [desde, hasta]
    filtro_tipo = ""
    join_insumos = ""
    if tipos:
        placeholders = ",".join("?" for _ in tipos)
        join_insumos = "JOIN insumos i ON i.id = dvi.insumo_id"
        filtro_tipo = f"AND i.tipo IN ({placeholders})"
        params.extend(tipos)

    query = f"""
        SELECT dvi.nombre_insumo AS nombre, SUM(dvi.cantidad_usada) AS cantidad
        FROM detalle_venta_insumos dvi
        JOIN detalle_venta dv ON dv.id = dvi.detalle_venta_id
        JOIN ventas v ON v.id = dv.venta_id
        {join_insumos}
        WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
        {filtro_tipo}
        GROUP BY dvi.nombre_insumo
        ORDER BY cantidad DESC
    """
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [{"nombre": r["nombre"], "cantidad": r["cantidad"]} for r in rows]


def detalle_ventas(desde: str, hasta: str) -> list[dict]:
    """Una fila por venta, con los productos vendidos concatenados —
    para el detalle transaccional del Excel extendido."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT v.id AS venta_id, v.fecha_hora, u.nombre AS empleado,
                      GROUP_CONCAT(dv.nombre_producto, ', ') AS productos,
                      v.subtotal, v.descuento_pct, v.descuento_monto, v.total, v.metodo_pago
               FROM ventas v
               JOIN usuarios u ON u.id = v.usuario_id
               LEFT JOIN detalle_venta dv ON dv.venta_id = v.id
               WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
               GROUP BY v.id
               ORDER BY v.fecha_hora""",
            (desde, hasta),
        ).fetchall()
    return [dict(r) for r in rows]


def resumen_gastos(desde: str, hasta: str) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(monto), 0) AS total FROM gastos WHERE fecha BETWEEN ? AND ?",
            (desde, hasta),
        ).fetchone()
    return row["total"]


def gastos_por_categoria(desde: str, hasta: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT categoria, SUM(monto) AS total
               FROM gastos
               WHERE fecha BETWEEN ? AND ?
               GROUP BY categoria
               ORDER BY total DESC""",
            (desde, hasta),
        ).fetchall()
    return [{"categoria": r["categoria"], "total": r["total"]} for r in rows]


def promociones_uso(desde: str, hasta: str) -> list[dict]:
    """Cuántas veces se usó cada promoción con nombre, y cuánto descuento
    acumuló, dentro del rango. Solo cuenta ventas que se cobraron con una
    promoción (no descuentos manuales ni los botones "generales")."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT p.nombre AS nombre, COUNT(*) AS num_usos, SUM(v.descuento_monto) AS descuento_total
               FROM ventas v
               JOIN promociones p ON p.id = v.promocion_id
               WHERE v.estado = 'completada' AND date(v.fecha_hora) BETWEEN ? AND ?
               GROUP BY v.promocion_id
               ORDER BY descuento_total DESC""",
            (desde, hasta),
        ).fetchall()
    return [
        {"nombre": r["nombre"], "num_usos": r["num_usos"], "descuento_total": r["descuento_total"]}
        for r in rows
    ]
