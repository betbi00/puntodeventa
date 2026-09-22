"""Catálogo de bebidas (precio fijo) y modal de extras: qué extra se
ofrece depende de bebida.tipo_extra — 'boba_perlas' (se puede marcar más
de uno) o 'pulpa' (una sola pulpa de fruta). Ninguno tiene costo
adicional, pero sí descuentan su propio inventario."""
import customtkinter as ctk
from PIL import Image

from config import MUNECOS_DIR
from services import inventario_service as inv
from services import venta_service as vs
from ui import theme

COLUMNAS = 3
TAMANO_MUNECO_BEBIDA = 72


# Variantes de color generadas a partir de boba.png / cafe.png (mismo
# dibujo, distinto tono de contorno) para que cada sabor se distinga a
# simple vista en vez de repetir siempre el mismo color.
VARIANTES_DISPONIBLES = {
    ("boba", "taro"), ("boba", "matcha"), ("boba", "chai"), ("boba", "fruta"),
    ("cafe", "taro"), ("cafe", "matcha"), ("cafe", "chai"),
    ("cafe", "oreo"), ("cafe", "mazapan"),
}


def _muneco_bebida(nombre_bebida: str) -> str:
    """Las bobas usan como base el muñeco de boba; el resto (Frappés) el
    del vaso de café — pero coloreado distinto según el sabor, para que
    no se vean todas idénticas. El Frappé de agua con pulpa de fruta usa
    la forma de vaso de boba (transparente, con domo): la del vaso de
    café para llevar no encajaba con una bebida fría de fruta."""
    nombre = nombre_bebida.strip().lower()

    if "taro" in nombre:
        sabor = "taro"
    elif "matcha" in nombre:
        sabor = "matcha"
    elif "chai" in nombre:
        sabor = "chai"
    elif "oreo" in nombre:
        sabor = "oreo"
    elif "mazap" in nombre:  # "Mazapán"
        sabor = "mazapan"
    elif "pulpa" in nombre:  # el sabor real lo elige el cliente al vender
        sabor = "fruta"
    else:
        sabor = None

    base = "boba" if (nombre.startswith("boba") or sabor == "fruta") else "cafe"

    if sabor and (base, sabor) in VARIANTES_DISPONIBLES:
        return f"{base}_{sabor}.png"
    return f"{base}.png"


class BebidaCatalogo(ctk.CTkFrame):
    def __init__(self, master, on_agregar):
        super().__init__(master, fg_color="transparent")
        self.on_agregar = on_agregar
        self._imagenes = {}  # bebida_id -> CTkImage, evita que el garbage collector las borre
        for col in range(COLUMNAS):
            self.grid_columnconfigure(col, weight=1)
        self._refrescar()

    def _refrescar(self):
        for widget in self.winfo_children():
            widget.destroy()
        bebidas = inv.listar_bebidas(incluir_inactivos=False)
        for index, bebida in enumerate(bebidas):
            fila, columna = divmod(index, COLUMNAS)
            self._tarjeta_bebida(bebida, fila, columna)

    def _tarjeta_bebida(self, bebida, fila, columna):
        card = ctk.CTkFrame(self, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_CARD, cursor="hand2")
        card.grid(row=fila, column=columna, padx=8, pady=8, sticky="nsew")

        imagen = Image.open(MUNECOS_DIR / _muneco_bebida(bebida.nombre))
        ctk_imagen = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=(TAMANO_MUNECO_BEBIDA, TAMANO_MUNECO_BEBIDA))
        self._imagenes[bebida.id] = ctk_imagen
        ctk.CTkLabel(card, image=ctk_imagen, text="").pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            card, text=bebida.nombre, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=16)
        ctk.CTkLabel(
            card, text=f"${bebida.precio:.2f}", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), text_color=theme.PINK_HOVER,
        ).pack(anchor="w", padx=16, pady=(0, 16))

        def abrir(_e=None, b=bebida):
            BebidaExtrasModal(self, b, on_agregar=self.on_agregar)

        card.bind("<Button-1>", abrir)
        for child in card.winfo_children():
            child.bind("<Button-1>", abrir)


class BebidaExtrasModal(ctk.CTkToplevel):
    def __init__(self, master, bebida, on_agregar):
        super().__init__(master)
        self.bebida = bebida
        self.on_agregar = on_agregar
        self.checkboxes = {}  # insumo_id -> (CTkCheckBox, Insumo) — modo boba_perlas
        self.opcion_pulpa = None  # tk.IntVar compartida entre los radio — modo pulpa
        self.radios_pulpa = {}  # insumo_id -> Insumo
        self.es_pulpa = bebida.tipo_extra == "pulpa"

        self.title(bebida.nombre)
        self.geometry("380x380")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text=self.bebida.nombre, font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 0))
        ctk.CTkLabel(
            self, text=f"${self.bebida.precio:.2f} · precio fijo", text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        if self.es_pulpa:
            self._build_pulpa()
        else:
            self._build_boba_perlas()

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=330, justify="left")
        self.label_error.pack(fill="x", padx=24, pady=(12, 0))

        ctk.CTkButton(
            self, text=f"+ Agregar ${self.bebida.precio:.2f}", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            height=48, command=self._agregar,
        ).pack(fill="x", padx=24, pady=(16, 24), side="bottom")

    def _build_boba_perlas(self):
        ctk.CTkLabel(
            self, text="Extras sin costo", anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=24)

        extras = inv.listar_insumos(tipo=["boba", "perla_explosiva"], incluir_inactivos=False)
        for insumo in extras:
            agotado = insumo.stock_actual <= 0
            texto = insumo.nombre + ("  (agotado)" if agotado else "")
            checkbox = ctk.CTkCheckBox(
                self, text=texto, state="disabled" if agotado else "normal",
                text_color=theme.TEXT_SECONDARY if agotado else theme.TEXT_PRIMARY,
                fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            )
            checkbox.pack(anchor="w", padx=24, pady=6)
            self.checkboxes[insumo.id] = (checkbox, insumo)

    def _build_pulpa(self):
        ctk.CTkLabel(
            self, text="Elige tu pulpa", anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=24)

        pulpas = inv.listar_insumos(tipo="pulpa", incluir_inactivos=False)
        self.opcion_pulpa = ctk.IntVar(value=0)
        for insumo in pulpas:
            agotado = insumo.stock_actual <= 0
            texto = insumo.nombre + ("  (agotado)" if agotado else "")
            radio = ctk.CTkRadioButton(
                self, text=texto, variable=self.opcion_pulpa, value=insumo.id,
                state="disabled" if agotado else "normal",
                text_color=theme.TEXT_SECONDARY if agotado else theme.TEXT_PRIMARY,
                fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            )
            radio.pack(anchor="w", padx=24, pady=6)
            self.radios_pulpa[insumo.id] = insumo

    def _agregar(self):
        if self.es_pulpa:
            if self.radios_pulpa and self.opcion_pulpa.get() == 0:
                self.label_error.configure(text="Elige una pulpa antes de continuar")
                return
            seleccionados = [self.opcion_pulpa.get()] if self.opcion_pulpa.get() else []
        else:
            seleccionados = [insumo.id for (cb, insumo) in self.checkboxes.values() if cb.get() == 1]
        try:
            item = vs.armar_bebida(self.bebida.id, seleccionados)
        except vs.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_agregar(item)
        self.destroy()
