"""Impresión de tickets ESC/POS en la Epson TM-T20III (conexión USB).

Si la impresora falla o no está disponible, se levanta ImpresionError sin
tocar la venta ya registrada en la base de datos — quien llame decide cómo
avisar (la UI ofrece reintentar más tarde). Por eso imprimir_venta() nunca
debe llamarse dentro de la misma transacción que registrar_venta().
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import NEGOCIO_NOMBRE, NEGOCIO_SUBTITULO, TICKET_MENSAJE_DESPEDIDA, TICKET_USB_PRODUCT_ID, TICKET_USB_VENDOR_ID
from models import usuario as usuario_model
from models import venta as venta_model

ANCHO_TICKET = 42  # caracteres por línea, típico de papel de 58-80mm


class ImpresionError(Exception):
    """La impresora no está disponible, no está configurada, o falló al imprimir."""


@dataclass
class LineaTicketItem:
    nombre: str
    precio: float
    insumos: list = field(default_factory=list)  # nombres de ingredientes/extras


@dataclass
class TicketData:
    encabezado: str
    subtitulo: str
    fecha_hora: str
    vendedor: str
    items: list  # list[LineaTicketItem]
    subtotal: float
    descuento_pct: float
    descuento_monto: float
    total: float
    metodo_pago: str
    mp_payment_id: Optional[str]
    despedida: str
    venta_id: Optional[int] = None


def datos_ticket_prueba() -> TicketData:
    """Datos de ejemplo para probar el formato del ticket sin tocar la base
    de datos ni requerir una venta real."""
    return TicketData(
        encabezado=NEGOCIO_NOMBRE,
        subtitulo=NEGOCIO_SUBTITULO,
        fecha_hora=datetime.now().strftime("%d/%m/%Y %H:%M"),
        vendedor="Vendedor Demo",
        items=[
            LineaTicketItem("Crepa", 68.0, ["Nutella", "Fresa"]),
            LineaTicketItem("Taro Milk Tea", 65.0, ["Boba", "Perlas explosivas"]),
        ],
        subtotal=133.0,
        descuento_pct=10,
        descuento_monto=13.3,
        total=119.7,
        metodo_pago="efectivo",
        mp_payment_id=None,
        despedida=TICKET_MENSAJE_DESPEDIDA,
        venta_id=None,
    )


def datos_ticket_de_venta(venta_id: int) -> TicketData:
    venta = venta_model.get_completa(venta_id)
    if not venta:
        raise ImpresionError(f"La venta #{venta_id} no existe")

    vendedor = usuario_model.get_by_id(venta.usuario_id)
    nombre_vendedor = vendedor.nombre if vendedor else f"Usuario #{venta.usuario_id}"

    items = [
        LineaTicketItem(
            nombre=detalle.nombre_producto,
            precio=detalle.subtotal_item,
            insumos=[i.nombre_insumo for i in detalle.insumos],
        )
        for detalle in venta.detalles
    ]

    try:
        fecha = datetime.strptime(venta.fecha_hora, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        fecha = venta.fecha_hora

    return TicketData(
        encabezado=NEGOCIO_NOMBRE,
        subtitulo=NEGOCIO_SUBTITULO,
        fecha_hora=fecha,
        vendedor=nombre_vendedor,
        items=items,
        subtotal=venta.subtotal,
        descuento_pct=venta.descuento_pct,
        descuento_monto=venta.descuento_monto,
        total=venta.total,
        metodo_pago=venta.metodo_pago,
        mp_payment_id=venta.mp_payment_id,
        despedida=TICKET_MENSAJE_DESPEDIDA,
        venta_id=venta.id,
    )


def _centrar(texto: str, ancho: int = ANCHO_TICKET) -> str:
    return texto.center(ancho)


def _linea_doble(izquierda: str, derecha: str, ancho: int = ANCHO_TICKET) -> str:
    espacio = max(1, ancho - len(izquierda) - len(derecha))
    return f"{izquierda}{' ' * espacio}{derecha}"


def _lineas_cuerpo(datos: TicketData) -> list[str]:
    """Genera el contenido del ticket como lista de líneas de texto plano.
    Se reutiliza tanto para la vista previa en pantalla como base del
    formato que se envía a la impresora."""
    lineas = [
        _centrar(datos.encabezado.upper()),
    ]
    if datos.subtitulo:
        lineas.append(_centrar(datos.subtitulo))
    lineas.append("=" * ANCHO_TICKET)
    lineas.append(f"Fecha: {datos.fecha_hora}")
    lineas.append(f"Vendedor: {datos.vendedor}")
    if datos.venta_id:
        lineas.append(f"Venta #{datos.venta_id}")
    lineas.append("-" * ANCHO_TICKET)

    for item in datos.items:
        lineas.append(_linea_doble(item.nombre, f"${item.precio:.2f}"))
        for insumo in item.insumos:
            lineas.append(f"  + {insumo}")

    lineas.append("-" * ANCHO_TICKET)
    lineas.append(_linea_doble("Subtotal", f"${datos.subtotal:.2f}"))
    if datos.descuento_pct:
        lineas.append(_linea_doble(f"Descuento ({datos.descuento_pct:g}%)", f"-${datos.descuento_monto:.2f}"))
    lineas.append(_linea_doble("TOTAL", f"${datos.total:.2f}"))
    lineas.append("-" * ANCHO_TICKET)

    metodo_texto = "Efectivo" if datos.metodo_pago == "efectivo" else "Tarjeta"
    lineas.append(f"Método de pago: {metodo_texto}")
    if datos.metodo_pago == "tarjeta" and datos.mp_payment_id:
        lineas.append(f"ID transacción MP: {datos.mp_payment_id}")

    lineas.append("=" * ANCHO_TICKET)
    lineas.append(_centrar(datos.despedida))
    return lineas


def renderizar_texto(datos: TicketData) -> str:
    """Vista previa en texto plano, igual a lo que se envía a imprimir."""
    return "\n".join(_lineas_cuerpo(datos))


def imprimir(datos: TicketData) -> None:
    """Envía el ticket a la impresora física. Lanza ImpresionError (sin
    tocar la base de datos) si la impresora no está configurada, no se
    encuentra, o falla a medio imprimir."""
    if TICKET_USB_VENDOR_ID is None or TICKET_USB_PRODUCT_ID is None:
        raise ImpresionError(
            "La impresora todavía no está configurada (falta TICKET_USB_VENDOR_ID / "
            "TICKET_USB_PRODUCT_ID en config.py)."
        )

    try:
        from escpos.printer import Usb
    except ImportError as e:
        raise ImpresionError("La librería python-escpos no está instalada.") from e

    try:
        # python-escpos no tiene un perfil "TM-T20III" exacto; "TM-T20II" usa
        # el mismo juego de comandos ESC/POS básicos y es compatible aquí.
        impresora = Usb(TICKET_USB_VENDOR_ID, TICKET_USB_PRODUCT_ID, profile="TM-T20II")
    except Exception as e:
        raise ImpresionError(f"No se pudo conectar con la impresora: {e}") from e

    try:
        impresora.set(align="center", bold=True, width=2, height=2)
        impresora.text(datos.encabezado.upper() + "\n")
        impresora.set(align="center", bold=False, width=1, height=1)
        if datos.subtitulo:
            impresora.text(datos.subtitulo + "\n")
        impresora.text("-" * ANCHO_TICKET + "\n")

        impresora.set(align="left")
        impresora.text(f"Fecha: {datos.fecha_hora}\n")
        impresora.text(f"Vendedor: {datos.vendedor}\n")
        if datos.venta_id:
            impresora.text(f"Venta #{datos.venta_id}\n")
        impresora.text("-" * ANCHO_TICKET + "\n")

        for item in datos.items:
            impresora.text(_linea_doble(item.nombre, f"${item.precio:.2f}") + "\n")
            for insumo in item.insumos:
                impresora.text(f"  + {insumo}\n")

        impresora.text("-" * ANCHO_TICKET + "\n")
        impresora.text(_linea_doble("Subtotal", f"${datos.subtotal:.2f}") + "\n")
        if datos.descuento_pct:
            impresora.text(
                _linea_doble(f"Descuento ({datos.descuento_pct:g}%)", f"-${datos.descuento_monto:.2f}") + "\n"
            )
        impresora.set(bold=True)
        impresora.text(_linea_doble("TOTAL", f"${datos.total:.2f}") + "\n")
        impresora.set(bold=False)

        metodo_texto = "Efectivo" if datos.metodo_pago == "efectivo" else "Tarjeta"
        impresora.text(f"Metodo de pago: {metodo_texto}\n")
        if datos.metodo_pago == "tarjeta" and datos.mp_payment_id:
            impresora.text(f"ID transaccion MP: {datos.mp_payment_id}\n")

        impresora.text("=" * ANCHO_TICKET + "\n")
        impresora.set(align="center")
        impresora.text(datos.despedida + "\n")
        impresora.cut()
    except Exception as e:
        raise ImpresionError(f"Falló la impresión: {e}") from e
    finally:
        try:
            impresora.close()
        except Exception:
            pass


def imprimir_venta(venta_id: int) -> None:
    """Imprime el ticket de una venta ya registrada. Si tiene éxito, marca
    ticket_impreso=1; si falla, propaga ImpresionError sin marcar nada (para
    que la UI pueda ofrecer reintentar)."""
    datos = datos_ticket_de_venta(venta_id)
    imprimir(datos)
    venta_model.marcar_ticket_impreso(venta_id, True)
