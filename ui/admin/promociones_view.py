"""Panel de promociones con nombre (ej. "Promoción día del niño"), que el
administrador da de alta desde el Dashboard. Cada promoción activa
aparece como botón de acceso rápido al cobrar en el punto de venta."""
import customtkinter as ctk

from services import promocion_service as promos
from ui import theme

MOSTRAR_RECIENTES = 8


class PromocionesPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self._build()
        self._refrescar()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header, text="Promociones", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            header, text="+ Nueva promoción", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")
        ctk.CTkLabel(
            self, text="Las promociones activas aparecen como botón de acceso rápido al cobrar en el punto de venta.",
            text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            wraplength=500, justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.lista_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.lista_frame.pack(fill="x", padx=8, pady=(0, 12))

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()

        promociones = promos.listar_promociones()[:MOSTRAR_RECIENTES]
        if not promociones:
            ctk.CTkLabel(
                self.lista_frame, text="Todavía no hay promociones registradas.", text_color=theme.TEXT_SECONDARY,
            ).pack(pady=8)
            return

        for promo in promociones:
            self._fila_promocion(promo)

    def _fila_promocion(self, promo):
        row = ctk.CTkFrame(self.lista_frame, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_INPUT)
        row.pack(fill="x", pady=4, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        ctk.CTkLabel(
            info, text=promo.nombre, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")
        estado_texto = "Activa" if promo.activo else "Inactiva"
        estado_color = theme.SUCCESS if promo.activo else theme.TEXT_SECONDARY
        detalle = ctk.CTkFrame(info, fg_color="transparent")
        detalle.pack(anchor="w")
        ctk.CTkLabel(
            detalle, text=f"{promo.porcentaje:g}% de descuento · ", text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(side="left")
        ctk.CTkLabel(
            detalle, text=estado_texto, text_color=estado_color,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold"),
        ).pack(side="left")

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right", padx=8)
        ctk.CTkButton(
            acciones, text="Editar", width=64, height=28, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda p=promo: self._abrir_form_editar(p),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acciones, text=("Desactivar" if promo.activo else "Activar"), width=80, height=28,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, command=lambda p=promo: self._toggle_activo(p),
        ).pack(side="left", padx=2)

    def _toggle_activo(self, promo):
        promos.set_activo_promocion(promo.id, not promo.activo)
        self._refrescar()

    def _abrir_form_nuevo(self):
        FormularioPromocion(self, promocion=None, on_guardado=self._refrescar)

    def _abrir_form_editar(self, promo):
        FormularioPromocion(self, promocion=promo, on_guardado=self._refrescar)


class FormularioPromocion(ctk.CTkToplevel):
    def __init__(self, master, promocion, on_guardado):
        super().__init__(master)
        self.promocion = promocion
        self.on_guardado = on_guardado

        self.title("Editar promoción" if promocion else "Nueva promoción")
        self.geometry("380x340")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Nombre de la promoción", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_nombre = ctk.CTkEntry(
            self, fg_color=theme.BG_INPUT, border_width=0, placeholder_text="Ej. Promoción día del niño",
        )
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))
        if self.promocion:
            self.entry_nombre.insert(0, self.promocion.nombre)

        ctk.CTkLabel(self, text="Porcentaje de descuento (%)", anchor="w").pack(fill="x", padx=24)
        self.entry_porcentaje = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_porcentaje.pack(fill="x", padx=24, pady=(0, 12))
        if self.promocion:
            self.entry_porcentaje.insert(0, str(self.promocion.porcentaje))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=330, justify="left")
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, height=48,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24), side="bottom")

    def _guardar(self):
        try:
            porcentaje = float(self.entry_porcentaje.get())
        except ValueError:
            self.label_error.configure(text="El porcentaje debe ser un número")
            return

        nombre = self.entry_nombre.get()
        try:
            if self.promocion:
                promos.actualizar_promocion(self.promocion.id, nombre, porcentaje)
            else:
                promos.crear_promocion(nombre, porcentaje)
        except promos.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()
