"""Lógica de negocio del carrito de venta: armar productos personalizados,
calcular totales y registrar la venta de forma atómica (venta + detalle +
descuento de inventario correspondiente).

El método de pago 'tarjeta' se registra igual que 'efectivo' por ahora
(mp_payment_id / mp_status quedan en None) — la conexión real con la
terminal Mercado Pago Point se conecta en la Fase 5, en el mismo punto
donde hoy se llama a registrar_venta.
"""
from dataclasses import dataclass, field
from typing import Optional

from db.connection import get_connection
from models import bebida as bebida_model
from models import insumo as insumo_model
from models import producto_base as producto_base_model
from services import inventario_service

EXTRAS_BEBIDA_TIPOS = ("boba", "perla_explosiva")
METODOS_PAGO_VALIDOS = ("efectivo", "tarjeta")


class ValidationError(Exception):
    """Datos de entrada inválidos o stock insuficiente."""


@dataclass
class InsumoUsado:
    insumo_id: int
    nombre: str
    precio_extra: float
    cantidad_usada: float = 1


@dataclass
class ItemCarrito:
    tipo_producto: str  # 'producto_base' | 'bebida'
    nombre_producto: str
    precio_unitario: float
    producto_base_id: Optional[int] = None
    bebida_id: Optional[int] = None
    cantidad: int = 1
    insumos: list = field(default_factory=list)  # list[InsumoUsado]

    @property
    def subtotal(self) -> float:
        return self.precio_unitario * self.cantidad

    @property
    def descripcion_insumos(self) -> str:
        return ", ".join(i.nombre for i in self.insumos) if self.insumos else ""


def armar_producto_base(producto_base_id: int, insumo_ids_seleccionados: list[int]) -> ItemCarrito:
    """Calcula el precio de una crepa/waffle armada según los ingredientes
    elegidos. Valida que cada ingrediente exista, esté activo y tenga
    stock disponible."""
    producto = producto_base_model.get_by_id(producto_base_id)
    if not producto or not producto.activo:
        raise ValidationError("El producto base no existe o no está disponible")

    insumos_usados = []
    precio = producto.precio_base
    for insumo_id in insumo_ids_seleccionados:
        insumo = insumo_model.get_by_id(insumo_id)
        if not insumo or not insumo.activo:
            raise ValidationError("Uno de los ingredientes seleccionados ya no está disponible")
        if insumo.stock_actual <= 0:
            raise ValidationError(f'"{insumo.nombre}" está agotado')
        insumos_usados.append(InsumoUsado(insumo.id, insumo.nombre, insumo.precio_extra))
        precio += insumo.precio_extra

    return ItemCarrito(
        tipo_producto="producto_base",
        nombre_producto=producto.nombre,
        precio_unitario=precio,
        producto_base_id=producto.id,
        insumos=insumos_usados,
    )


def armar_bebida(bebida_id: int, extra_insumo_ids: Optional[list[int]] = None) -> ItemCarrito:
    """Bebida de precio fijo con extras opcionales (boba / perlas
    explosivas) que no suman costo pero sí se descuentan de su propio
    stock. Se puede marcar más de un extra a la vez."""
    bebida = bebida_model.get_by_id(bebida_id)
    if not bebida or not bebida.activo:
        raise ValidationError("La bebida no existe o no está disponible")
    if bebida.stock_actual <= 0:
        raise ValidationError(f'"{bebida.nombre}" está agotada')

    extras_usados = []
    for insumo_id in (extra_insumo_ids or []):
        insumo = insumo_model.get_by_id(insumo_id)
        if not insumo or not insumo.activo:
            raise ValidationError("Uno de los extras seleccionados ya no está disponible")
        if insumo.tipo not in EXTRAS_BEBIDA_TIPOS:
            raise ValidationError(f'"{insumo.nombre}" no es un extra válido para bebidas')
        if insumo.stock_actual <= 0:
            raise ValidationError(f'"{insumo.nombre}" está agotado')
        extras_usados.append(InsumoUsado(insumo.id, insumo.nombre, 0))

    return ItemCarrito(
        tipo_producto="bebida",
        nombre_producto=bebida.nombre,
        precio_unitario=bebida.precio,
        bebida_id=bebida.id,
        insumos=extras_usados,
    )


class Carrito:
    """Estado de la venta en construcción, antes de cobrar."""

    def __init__(self):
        self.items: list[ItemCarrito] = []

    def agregar(self, item: ItemCarrito) -> None:
        self.items.append(item)

    def eliminar(self, index: int) -> None:
        del self.items[index]

    def vaciar(self) -> None:
        self.items.clear()

    @property
    def esta_vacio(self) -> bool:
        return len(self.items) == 0

    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)

    def calcular_descuento_y_total(self, descuento_pct: float) -> tuple[float, float]:
        subtotal = self.subtotal
        descuento_monto = round(subtotal * (descuento_pct / 100), 2)
        total = round(subtotal - descuento_monto, 2)
        return descuento_monto, total


def registrar_venta(
    carrito: Carrito, usuario_id: int, descuento_pct: float, metodo_pago: str,
    mp_payment_id: Optional[str] = None, mp_status: Optional[str] = None, promocion_id: Optional[int] = None,
) -> int:
    """Registra la venta completa de forma atómica: si algún insumo no
    tiene stock suficiente, no se guarda nada (ni la venta ni ningún
    descuento de inventario) — todo o nada.

    promocion_id es opcional: se guarda cuando el descuento vino de una
    promoción con nombre (elegida con un botón en el cobro), para poder
    reportar cuánto se usó cada una. Un descuento manual o uno de los
    botones "generales" no llevan promocion_id.
    """
    if carrito.esta_vacio:
        raise ValidationError("El carrito está vacío")
    if metodo_pago not in METODOS_PAGO_VALIDOS:
        raise ValidationError(f"Método de pago inválido: {metodo_pago}")
    if not (0 <= descuento_pct <= 100):
        raise ValidationError("El descuento debe estar entre 0 y 100%")

    subtotal = carrito.subtotal
    descuento_monto, total = carrito.calcular_descuento_y_total(descuento_pct)

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO ventas
               (usuario_id, subtotal, descuento_pct, descuento_monto, promocion_id, total, metodo_pago, mp_payment_id, mp_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                usuario_id, subtotal, descuento_pct, descuento_monto, promocion_id,
                total, metodo_pago, mp_payment_id, mp_status,
            ),
        )
        venta_id = cursor.lastrowid

        for item in carrito.items:
            cursor_detalle = conn.execute(
                """INSERT INTO detalle_venta
                   (venta_id, tipo_producto, producto_base_id, bebida_id, nombre_producto, precio_unitario, cantidad, subtotal_item)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    venta_id, item.tipo_producto, item.producto_base_id, item.bebida_id,
                    item.nombre_producto, item.precio_unitario, item.cantidad, item.subtotal,
                ),
            )
            detalle_id = cursor_detalle.lastrowid

            if item.tipo_producto == "bebida":
                try:
                    inventario_service.descontar_stock_bebida_por_venta(
                        conn, item.bebida_id, item.cantidad, usuario_id, venta_id,
                    )
                except inventario_service.ValidationError as e:
                    raise ValidationError(str(e)) from e

            for insumo_usado in item.insumos:
                conn.execute(
                    """INSERT INTO detalle_venta_insumos
                       (detalle_venta_id, insumo_id, nombre_insumo, precio_extra, cantidad_usada)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        detalle_id, insumo_usado.insumo_id, insumo_usado.nombre,
                        insumo_usado.precio_extra, insumo_usado.cantidad_usada,
                    ),
                )
                try:
                    inventario_service.descontar_stock_por_venta(
                        conn, insumo_usado.insumo_id, insumo_usado.cantidad_usada, usuario_id, venta_id,
                    )
                except inventario_service.ValidationError as e:
                    # Se re-lanza como ValidationError de este módulo para que quien
                    # llame a registrar_venta solo necesite conocer esta excepción.
                    # La transacción completa (venta + detalle + descuentos previos)
                    # se revierte igual, porque get_connection hace rollback on error.
                    raise ValidationError(str(e)) from e

    return venta_id
