"""Permite hacer scroll arrastrando con el dedo (o el mouse) en cualquier
parte de un CTkScrollableFrame, no solo agarrando la barra lateral —
indispensable en las pantallas táctiles con las que se usa la app en
tienda (un dedo no puede "agarrar" una barra de 6px de ancho).

Tkinter no propaga los eventos de un widget hijo a las bindings de su
padre, así que el arrastre se registra en cada widget de la subrama, con
tkinter.Misc.bind directamente en vez del .bind() propio de
CTkFrame/CTkLabel/CTkButton — ese ya reenvía la binding a sus propios
hijos internos (el canvas/label real que recibe el evento), así que
volver a usarlo al bajar por la recursión duplicaría el manejador sobre
esos mismos hijos y el scroll avanzaría al doble de velocidad.

Además de las filas de contenido (que se destruyen y recrean en cada
`_refrescar()`), también se registra directamente en el canvas interno
del CTkScrollableFrame y en la tarjeta redondeada que lo envuelve
(`_parent_canvas`/`_parent_frame` de customtkinter) — esos dos SÍ
persisten entre refrescos, así que se marcan una sola vez. Sin esto,
arrastrar en un espacio verdaderamente vacío (el borde de la tarjeta,
o el hueco debajo de la última fila cuando la lista es corta) no hacía
nada, porque ningún widget de contenido cubre esos píxeles.

No se intenta cancelar el click de un botón cuando el arrastre empieza
encima de él: CTkButton dispara su acción en el press, no en el
release, así que para cuando detectamos que hubo arrastre el click ya
se disparó. En la práctica no es un problema real, porque la mayor
parte de cada fila (nombre, precio, stock) no tiene ningún click
asociado — arrastrar ahí para bajar la lista no dispara nada.

Hay que volver a llamar a `habilitar_scroll_tactil` cada vez que se
destruyen y recrean los widgets hijos (por ejemplo, al final de un
`_refrescar()`), porque los widgets nuevos no traen el manejador."""
import tkinter

UMBRAL_ARRASTRE_PX = 6


def _buscar_canvas_ancestro(widget):
    """Sube por `.master` hasta encontrar el canvas interno del
    CTkScrollableFrame dueño de este widget (incluyéndolo a él mismo).
    Sirve para poder llamar la función también desde un panel anidado
    que vive DENTRO de otra vista con scroll, sin tener que pasarle el
    frame scrollable exacto (ver GastosPanel/PromocionesPanel)."""
    actual = widget
    while actual is not None:
        canvas = getattr(actual, "_parent_canvas", None)
        if canvas is not None:
            return canvas
        actual = getattr(actual, "master", None)
    return None


def habilitar_scroll_tactil(widget):
    canvas = _buscar_canvas_ancestro(widget)
    if canvas is None:
        return  # no está dentro de ningún CTkScrollableFrame

    estado = {"y0": 0}

    def _en_presionar(event):
        estado["y0"] = event.y_root

    def _en_mover(event):
        delta = event.y_root - estado["y0"]
        if abs(delta) < UMBRAL_ARRASTRE_PX:
            return
        bbox = canvas.bbox("all")
        if bbox:
            alto_contenido = bbox[3] - bbox[1]
            alto_visible = canvas.winfo_height()
            if alto_contenido > alto_visible:
                fraccion = canvas.yview()[0] - delta / alto_contenido
                canvas.yview_moveto(max(0.0, min(1.0, fraccion)))
        estado["y0"] = event.y_root

    def _marcar(w):
        tkinter.Misc.bind(w, "<ButtonPress-1>", _en_presionar, add="+")
        tkinter.Misc.bind(w, "<B1-Motion>", _en_mover, add="+")
        for hijo in w.winfo_children():
            _marcar(hijo)

    _marcar(widget)

    # canvas y tarjeta no se destruyen entre refrescos (a diferencia de
    # las filas): se marcan una sola vez para no ir apilando manejadores
    # duplicados cada vez que se llama a esta función.
    for fijo in (canvas, getattr(canvas, "master", None)):
        if fijo is not None and not getattr(fijo, "_scroll_tactil_listo", False):
            tkinter.Misc.bind(fijo, "<ButtonPress-1>", _en_presionar, add="+")
            tkinter.Misc.bind(fijo, "<B1-Motion>", _en_mover, add="+")
            fijo._scroll_tactil_listo = True
