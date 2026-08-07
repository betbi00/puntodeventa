"""Lógica de negocio de inventario: insumos, bebidas, productos base y
movimientos de stock."""
from typing import Optional

from db.connection import get_connection
from models import bebida as bebida_model
from models import insumo as insumo_model
from models import movimiento_inventario as movimiento_model
from models import producto_base as producto_base_model
from models.insumo import Insumo


class ValidationError(Exception):
    """Datos de entrada inválidos."""


# ---------------------------------------------------------------------------
# Insumos (ingredientes, boba, perlas explosivas)
# ---------------------------------------------------------------------------

def listar_insumos(tipo=None, incluir_inactivos: bool = True) -> list[Insumo]:
    """tipo acepta un solo tipo ('ingrediente') o una lista ('boba', 'perla_explosiva')."""
    return insumo_model.listar(tipo=tipo, incluir_inactivos=incluir_inactivos)


def crear_insumo(
    nombre: str, tipo: str, aplica_a: str, precio_extra: float,
    unidad_medida: str, stock_inicial: float, stock_minimo: float,
) -> Insumo:
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if tipo not in insumo_model.TIPOS_VALIDOS:
        raise ValidationError(f"Tipo inválido: {tipo}")
    if aplica_a not in insumo_model.APLICA_A_VALIDOS:
        raise ValidationError(f"'aplica_a' inválido: {aplica_a}")
    if stock_inicial < 0 or stock_minimo < 0:
        raise ValidationError("El stock no puede ser negativo")
    # La boba y las perlas explosivas nunca tienen costo extra para el cliente
    if tipo != "ingrediente":
        precio_extra = 0
    elif precio_extra < 0:
        raise ValidationError("El precio extra no puede ser negativo")
    return insumo_model.crear(nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_inicial, stock_minimo)


def actualizar_insumo(
    insumo_id: int, nombre: str, aplica_a: str, precio_extra: float,
    unidad_medida: str, stock_minimo: float,
) -> None:
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if aplica_a not in insumo_model.APLICA_A_VALIDOS:
        raise ValidationError(f"'aplica_a' inválido: {aplica_a}")
    if stock_minimo < 0:
        raise ValidationError("El stock mínimo no puede ser negativo")
    insumo = insumo_model.get_by_id(insumo_id)
    if not insumo:
        raise ValidationError("El insumo no existe")
    if insumo.tipo != "ingrediente":
        precio_extra = 0
    elif precio_extra < 0:
        raise ValidationError("El precio extra no puede ser negativo")
    insumo_model.actualizar_datos(insumo_id, nombre, aplica_a, precio_extra, unidad_medida, stock_minimo)


def set_activo_insumo(insumo_id: int, activo: bool) -> None:
    insumo_model.set_activo(insumo_id, activo)


def ajustar_stock(
    insumo_id: int, tipo: str, cantidad: float, usuario_id: int, motivo: Optional[str] = None,
) -> Insumo:
    """Único punto de entrada para cambiar stock_actual. El UPDATE del stock y
    el INSERT del movimiento ocurren en la misma transacción, para que el
    cambio y su rastro de auditoría (quién, cuándo, por qué) sean atómicos:
    nunca puede quedar un cambio de stock sin su movimiento correspondiente.
    """
    if tipo not in ("entrada", "ajuste"):
        raise ValidationError(f"Tipo de movimiento inválido para un ajuste manual: {tipo}")
    if cantidad == 0:
        raise ValidationError("La cantidad del movimiento no puede ser cero")
    if tipo == "entrada" and cantidad <= 0:
        raise ValidationError("Una entrada debe ser una cantidad positiva")
    if tipo == "ajuste" and not motivo:
        raise ValidationError("El motivo es obligatorio para un ajuste manual de stock")

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()
        if not row:
            raise ValidationError("El insumo no existe")
        insumo = Insumo.from_row(row)

        nuevo_stock = insumo.stock_actual + cantidad
        if nuevo_stock < 0:
            raise ValidationError(
                f"El stock no puede quedar negativo (actual: {insumo.stock_actual}, "
                f"movimiento: {cantidad})"
            )

        conn.execute("UPDATE insumos SET stock_actual = ? WHERE id = ?", (nuevo_stock, insumo_id))
        movimiento_model.crear(
            conn, insumo_id=insumo_id, tipo=tipo, cantidad=cantidad,
            stock_resultante=nuevo_stock, usuario_id=usuario_id, motivo=motivo,
        )

    return insumo_model.get_by_id(insumo_id)


def historial_movimientos(insumo_id: int):
    return movimiento_model.listar_por_insumo(insumo_id)


def descontar_stock_por_venta(conn, insumo_id: int, cantidad_usada: float, usuario_id: int, venta_id: int) -> None:
    """Descuenta stock por una venta ya en curso. A diferencia de
    ajustar_stock, recibe una conexión abierta para insertarse en la misma
    transacción que el resto de la venta (services/venta_service.py):
    si algo falla después (p. ej. otro insumo sin stock suficiente), todo
    se revierte junto, incluyendo este descuento.
    """
    row = conn.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()
    if not row:
        raise ValidationError(f"El insumo #{insumo_id} no existe")
    insumo = Insumo.from_row(row)

    nuevo_stock = insumo.stock_actual - cantidad_usada
    if nuevo_stock < 0:
        raise ValidationError(
            f'Stock insuficiente de "{insumo.nombre}": disponible {insumo.stock_actual:g}, '
            f"se requieren {cantidad_usada:g}"
        )

    conn.execute("UPDATE insumos SET stock_actual = ? WHERE id = ?", (nuevo_stock, insumo_id))
    movimiento_model.crear(
        conn, insumo_id=insumo_id, tipo="venta", cantidad=-cantidad_usada,
        stock_resultante=nuevo_stock, usuario_id=usuario_id, referencia_venta_id=venta_id,
    )


# ---------------------------------------------------------------------------
# Bebidas
# ---------------------------------------------------------------------------

def listar_bebidas(incluir_inactivos: bool = True):
    return bebida_model.listar(incluir_inactivos=incluir_inactivos)


def crear_bebida(nombre: str, precio: float, stock_inicial: float = 0, stock_minimo: float = 0):
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if precio <= 0:
        raise ValidationError("El precio debe ser mayor a cero")
    if stock_inicial < 0 or stock_minimo < 0:
        raise ValidationError("El stock no puede ser negativo")
    return bebida_model.crear(nombre, precio, stock_inicial, stock_minimo)


def actualizar_bebida(bebida_id: int, nombre: str, precio: float, stock_minimo: float):
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if precio <= 0:
        raise ValidationError("El precio debe ser mayor a cero")
    if stock_minimo < 0:
        raise ValidationError("El stock mínimo no puede ser negativo")
    bebida_model.actualizar(bebida_id, nombre, precio, stock_minimo)


def set_activo_bebida(bebida_id: int, activo: bool):
    bebida_model.set_activo(bebida_id, activo)


def ajustar_stock_bebida(
    bebida_id: int, tipo: str, cantidad: float, usuario_id: int, motivo: Optional[str] = None,
):
    """Equivalente a ajustar_stock pero para bebidas: mismo único punto de
    entrada para cambiar stock_actual, con el UPDATE y el movimiento de
    auditoría en la misma transacción."""
    if tipo not in ("entrada", "ajuste"):
        raise ValidationError(f"Tipo de movimiento inválido para un ajuste manual: {tipo}")
    if cantidad == 0:
        raise ValidationError("La cantidad del movimiento no puede ser cero")
    if tipo == "entrada" and cantidad <= 0:
        raise ValidationError("Una entrada debe ser una cantidad positiva")
    if tipo == "ajuste" and not motivo:
        raise ValidationError("El motivo es obligatorio para un ajuste manual de stock")

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM bebidas WHERE id = ?", (bebida_id,)).fetchone()
        if not row:
            raise ValidationError("La bebida no existe")
        bebida = bebida_model.Bebida.from_row(row)

        nuevo_stock = bebida.stock_actual + cantidad
        if nuevo_stock < 0:
            raise ValidationError(
                f"El stock no puede quedar negativo (actual: {bebida.stock_actual}, "
                f"movimiento: {cantidad})"
            )

        conn.execute("UPDATE bebidas SET stock_actual = ? WHERE id = ?", (nuevo_stock, bebida_id))
        movimiento_model.crear(
            conn, bebida_id=bebida_id, tipo=tipo, cantidad=cantidad,
            stock_resultante=nuevo_stock, usuario_id=usuario_id, motivo=motivo,
        )

    return bebida_model.get_by_id(bebida_id)


def historial_movimientos_bebida(bebida_id: int):
    return movimiento_model.listar_por_bebida(bebida_id)


def descontar_stock_bebida_por_venta(conn, bebida_id: int, cantidad_usada: float, usuario_id: int, venta_id: int) -> None:
    """Descuenta stock de una bebida por una venta ya en curso. Igual que
    descontar_stock_por_venta, recibe una conexión abierta para insertarse
    en la misma transacción que el resto de la venta."""
    row = conn.execute("SELECT * FROM bebidas WHERE id = ?", (bebida_id,)).fetchone()
    if not row:
        raise ValidationError(f"La bebida #{bebida_id} no existe")
    bebida = bebida_model.Bebida.from_row(row)

    nuevo_stock = bebida.stock_actual - cantidad_usada
    if nuevo_stock < 0:
        raise ValidationError(
            f'Stock insuficiente de "{bebida.nombre}": disponible {bebida.stock_actual:g}, '
            f"se requieren {cantidad_usada:g}"
        )

    conn.execute("UPDATE bebidas SET stock_actual = ? WHERE id = ?", (nuevo_stock, bebida_id))
    movimiento_model.crear(
        conn, bebida_id=bebida_id, tipo="venta", cantidad=-cantidad_usada,
        stock_resultante=nuevo_stock, usuario_id=usuario_id, referencia_venta_id=venta_id,
    )


# ---------------------------------------------------------------------------
# Productos base (Crepa, Waffle)
# ---------------------------------------------------------------------------

def listar_productos_base(incluir_inactivos: bool = True):
    return producto_base_model.listar(incluir_inactivos=incluir_inactivos)


def crear_producto_base(nombre: str, precio_base: float):
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if precio_base <= 0:
        raise ValidationError("El precio base debe ser mayor a cero")
    if producto_base_model.existe_nombre(nombre):
        raise ValidationError(f"Ya existe un producto base llamado '{nombre}'")
    return producto_base_model.crear(nombre, precio_base)


def actualizar_producto_base(producto_id: int, nombre: str, precio_base: float):
    nombre = nombre.strip()
    if not nombre:
        raise ValidationError("El nombre es obligatorio")
    if precio_base <= 0:
        raise ValidationError("El precio base debe ser mayor a cero")
    producto_base_model.actualizar(producto_id, nombre, precio_base)


def set_activo_producto_base(producto_id: int, activo: bool):
    producto_base_model.set_activo(producto_id, activo)
