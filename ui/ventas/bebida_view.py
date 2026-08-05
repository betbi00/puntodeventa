"""Catálogo de bebidas (precio fijo) y modal de extras: boba y/o perlas
explosivas, sin costo adicional pero descontando su propio inventario."""
import customtkinter as ctk

from services import inventario_service as inv
from services import venta_service as vs
from ui import theme

COLUMNAS = 3


class BebidaCatalogo(ctk.CTkScrollableFrame):
    def __init__(self, master, on_agregar):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.on_agregar = on_agregar
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

        ctk.CTkLabel(
            card, text="🥤", width=44, height=44, fg_color=theme.BLUE_SOFT, corner_radius=22,
            font=(theme.FONT_FAMILY, 18),
        ).pack(anchor="w", padx=16, pady=(16, 8))
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
        self.checkboxes = {}  # insumo_id -> (CTkCheckBox, Insumo)

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

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=330, justify="left")
        self.label_error.pack(fill="x", padx=24, pady=(12, 0))

        ctk.CTkButton(
            self, text=f"+ Agregar ${self.bebida.precio:.2f}", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            height=48, command=self._agregar,
        ).pack(fill="x", padx=24, pady=(16, 24), side="bottom")

    def _agregar(self):
        seleccionados = [insumo.id for (cb, insumo) in self.checkboxes.values() if cb.get() == 1]
        try:
            item = vs.armar_bebida(self.bebida.id, seleccionados)
        except vs.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_agregar(item)
        self.destroy()
