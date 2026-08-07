"""Generación del reporte en PDF: encabezado, KPIs, gráficas y todas las
tablas de datos (productos, empleados, promociones, consumo, gastos,
detalle de ventas) para el mismo rango de fechas que se ve en el
Dashboard. Reemplaza la exportación a Excel."""
import io

from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from config import NEGOCIO_NOMBRE, NEGOCIO_SUBTITULO
from services import gasto_service
from services import reporte_service as rep

TIPOS_EXTRAS_BEBIDA = ["boba", "perla_explosiva"]

# Misma paleta que la UI (rosa/azul pastel), pero como colores independientes
# aquí: este servicio no debe importar ui/theme.py (los servicios no
# dependen de la capa de interfaz).
ROSA = colors.HexColor("#F1A7C6")
ROSA_SUAVE = colors.HexColor("#FCE8F0")
AZUL = colors.HexColor("#AFD6F2")
AZUL_SUAVE = colors.HexColor("#E8F3FC")
TEXTO = colors.HexColor("#22242B")
TEXTO_SECUNDARIO = colors.HexColor("#8A8D96")
BORDE = colors.HexColor("#ECE7EA")

ANCHO_PAGINA_UTIL = letter[0] - 3.6 * cm


def exportar_pdf(desde: str, hasta: str, ruta_destino: str) -> None:
    estilos = _estilos()

    resumen = rep.resumen_ventas(desde, hasta)
    gastos_total = rep.resumen_gastos(desde, hasta)
    utilidad_neta = resumen["ingresos_totales"] - gastos_total

    elementos = []
    elementos.append(Paragraph(NEGOCIO_NOMBRE, estilos["titulo"]))
    elementos.append(Paragraph(NEGOCIO_SUBTITULO, estilos["subtitulo"]))
    elementos.append(Paragraph(f"Reporte de ventas · {desde} a {hasta}", estilos["subtitulo"]))
    elementos.append(Spacer(1, 14))

    elementos.append(_tabla_kpis(resumen, gastos_total, utilidad_neta))
    elementos.append(Spacer(1, 16))

    elementos.append(_fila_graficas(
        _grafica_ventas_por_dia(rep.ventas_por_dia(desde, hasta)),
        _grafica_metodo_pago(resumen),
    ))
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Productos más vendidos", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.productos_mas_vendidos(desde, hasta, limite=15),
        ["Producto", "Cantidad", "Ingresos"],
        lambda d: [d["nombre"], str(d["cantidad"]), f"${d['ingresos']:.2f}"],
        [9 * cm, 3.5 * cm, 4.5 * cm], estilos,
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Ventas por empleado", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.ventas_por_empleado(desde, hasta),
        ["Empleado", "Ventas", "Ingresos"],
        lambda d: [d["nombre"], str(d["num_ventas"]), f"${d['ingresos']:.2f}"],
        [9 * cm, 3.5 * cm, 4.5 * cm], estilos,
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Uso de promociones", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.promociones_uso(desde, hasta),
        ["Promoción", "Usos", "Descuento total"],
        lambda d: [d["nombre"], str(d["num_usos"]), f"${d['descuento_total']:.2f}"],
        [9 * cm, 3.5 * cm, 4.5 * cm], estilos,
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Consumo de boba y perlas explosivas", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.consumo_insumos(desde, hasta, tipos=TIPOS_EXTRAS_BEBIDA),
        ["Insumo", "Cantidad consumida"],
        lambda d: [d["nombre"], f"{d['cantidad']:g}"],
        [11 * cm, 6 * cm], estilos,
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Consumo de ingredientes", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.consumo_insumos(desde, hasta, tipos=["ingrediente"]),
        ["Ingrediente", "Cantidad consumida"],
        lambda d: [d["nombre"], f"{d['cantidad']:g}"],
        [11 * cm, 6 * cm], estilos,
    ))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph("Gastos", estilos["h2"]))
    gastos = gasto_service.listar_gastos(desde=desde, hasta=hasta)
    elementos.append(_tabla_o_vacio(
        gastos,
        ["Fecha", "Categoría", "Concepto", "Monto"],
        lambda g: [
            g.fecha, gasto_service.CATEGORIA_ETIQUETAS.get(g.categoria, g.categoria), g.concepto, f"${g.monto:.2f}",
        ],
        [3 * cm, 3.5 * cm, 7 * cm, 3.5 * cm], estilos,
    ))

    elementos.append(PageBreak())
    elementos.append(Paragraph("Apéndice: detalle de ventas", estilos["h2"]))
    elementos.append(_tabla_o_vacio(
        rep.detalle_ventas(desde, hasta),
        ["Venta #", "Fecha y hora", "Empleado", "Total", "Método"],
        lambda v: [
            str(v["venta_id"]), v["fecha_hora"], v["empleado"], f"${v['total']:.2f}",
            "Efectivo" if v["metodo_pago"] == "efectivo" else "Tarjeta",
        ],
        [2 * cm, 4.5 * cm, 5 * cm, 3 * cm, 3 * cm], estilos,
    ))

    doc = SimpleDocTemplate(
        ruta_destino, pagesize=letter,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    doc.build(elementos)


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], textColor=TEXTO, fontSize=20, alignment=TA_CENTER),
        "subtitulo": ParagraphStyle(
            "subtitulo", parent=base["Normal"], textColor=TEXTO_SECUNDARIO, fontSize=11, alignment=TA_CENTER,
        ),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=TEXTO, fontSize=13, spaceAfter=6),
        "vacio": ParagraphStyle("vacio", parent=base["Normal"], textColor=TEXTO_SECUNDARIO, fontSize=9),
    }


def _tabla_kpis(resumen, gastos_total, utilidad_neta):
    color_utilidad = colors.HexColor("#6FBF8F") if utilidad_neta >= 0 else colors.HexColor("#E0607A")
    filas = [
        ["Ventas del período", str(resumen["num_ventas"]), "Ingresos totales", f"${resumen['ingresos_totales']:.2f}"],
        ["Ticket promedio", f"${resumen['ticket_promedio']:.2f}", "Descuento aplicado", f"${resumen['descuento_total']:.2f}"],
        ["Gastos totales", f"${gastos_total:.2f}", "Utilidad neta", f"${utilidad_neta:.2f}"],
    ]
    tabla = Table(filas, colWidths=[4.5 * cm, 4 * cm, 4.5 * cm, 4 * cm])
    estilo = TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXTO_SECUNDARIO),
        ("TEXTCOLOR", (2, 0), (2, -1), TEXTO_SECUNDARIO),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (3, 2), (3, 2), color_utilidad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, BORDE),
        ("BACKGROUND", (0, 0), (-1, -1), ROSA_SUAVE),
    ])
    tabla.setStyle(estilo)
    return tabla


def _figura_a_imagen(fig, ancho_cm, alto_cm):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    return Image(buffer, width=ancho_cm * cm, height=alto_cm * cm)


def _grafica_ventas_por_dia(datos):
    fig = Figure(figsize=(4.6, 3), dpi=150, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_title("Ventas por día", fontsize=10, color="#22242B")
    if datos:
        dias = [d["dia"][5:] for d in datos]
        ingresos = [d["ingresos"] for d in datos]
        ax.bar(dias, ingresos, color="#F1A7C6")
        ax.tick_params(labelsize=7, colors="#8A8D96")
    else:
        ax.text(0.5, 0.5, "Sin ventas en este rango", ha="center", va="center", fontsize=9, color="#8A8D96")
        ax.set_xticks([])
        ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#ECE7EA")
    fig.tight_layout()
    return _figura_a_imagen(fig, 9, 5.9)


def _grafica_metodo_pago(resumen):
    fig = Figure(figsize=(3.2, 3), dpi=150, facecolor="white")
    ax = fig.add_subplot(111)
    ax.set_title("Ingresos por método de pago", fontsize=10, color="#22242B")
    valores = [resumen["ingresos_efectivo"], resumen["ingresos_tarjeta"]]
    if sum(valores) > 0:
        ax.pie(
            valores, labels=["Efectivo", "Tarjeta"], colors=["#F1A7C6", "#AFD6F2"],
            autopct="%1.0f%%", textprops={"fontsize": 8, "color": "#22242B"},
        )
    else:
        ax.text(0.5, 0.5, "Sin ventas", ha="center", va="center", fontsize=9, color="#8A8D96")
        ax.axis("off")
    fig.tight_layout()
    return _figura_a_imagen(fig, 6.5, 5.9)


def _fila_graficas(img_izquierda, img_derecha):
    tabla = Table([[img_izquierda, img_derecha]], colWidths=[9.5 * cm, 7 * cm])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
    ]))
    return tabla


def _tabla_o_vacio(datos, encabezados, fila_fn, anchos, estilos):
    if not datos:
        return Paragraph("Sin datos en este rango.", estilos["vacio"])

    filas = [encabezados] + [fila_fn(d) for d in datos]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_SUAVE),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEXTO),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tabla
