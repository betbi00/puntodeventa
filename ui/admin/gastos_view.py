"""Panel de gastos del negocio (renta, agua, luz, etc.), independientes de
las ventas — se registran aquí para que salgan restados en la utilidad
neta de los reportes de Excel."""
import datetime

import customtkinter as ctk

from services import gasto_service
from ui import theme

MOSTRAR_RECIENTES = 8


class GastosPanel(ctk.CTkFrame):
    def __init__(self, master, current_user):
        super().__init__(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.current_user = current_user
        self._build()
        self._refrescar()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header, text="Gastos del negocio", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            header, text="+ Nuevo gasto", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")
        ctk.CTkLabel(
            self, text="Renta, agua, luz y otros gastos que no vienen de una venta — se restan en la utilidad neta del Excel.",
            text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            wraplength=500, justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self.lista_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.lista_frame.pack(fill="x", padx=8, pady=(0, 12))

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()

        gastos = gasto_service.listar_gastos(limite=MOSTRAR_RECIENTES)
        if not gastos:
            ctk.CTkLabel(
                self.lista_frame, text="Todavía no hay gastos registrados.", text_color=theme.TEXT_SECONDARY,
            ).pack(pady=8)
            return

        for gasto in gastos:
            self._fila_gasto(gasto)

    def _fila_gasto(self, gasto):
        row = ctk.CTkFrame(self.lista_frame, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_INPUT)
        row.pack(fill="x", pady=4, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        ctk.CTkLabel(
            info, text=gasto.concepto, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")
        etiqueta_cat = gasto_service.CATEGORIA_ETIQUETAS.get(gasto.categoria, gasto.categoria)
        ctk.CTkLabel(
            info, text=f"{etiqueta_cat} · {gasto.fecha}", anchor="w", text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(anchor="w")

        ctk.CTkLabel(
            row, text=f"${gasto.monto:.2f}", text_color=theme.ERROR,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left", padx=8)

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right", padx=8)
        ctk.CTkButton(
            acciones, text="Editar", width=64, height=28, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda g=gasto: self._abrir_form_editar(g),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            acciones, text="Eliminar", width=70, height=28, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.ERROR, hover_color=theme.BG_HOVER,
            command=lambda g=gasto: self._confirmar_eliminar(g),
        ).pack(side="left", padx=2)

    def _abrir_form_nuevo(self):
        FormularioGasto(self, gasto=None, current_user=self.current_user, on_guardado=self._refrescar)

    def _abrir_form_editar(self, gasto):
        FormularioGasto(self, gasto=gasto, current_user=self.current_user, on_guardado=self._refrescar)

    def _confirmar_eliminar(self, gasto):
        ConfirmarEliminarGasto(self, gasto, on_confirmado=self._refrescar)


class FormularioGasto(ctk.CTkToplevel):
    def __init__(self, master, gasto, current_user, on_guardado):
        super().__init__(master)
        self.gasto = gasto
        self.current_user = current_user
        self.on_guardado = on_guardado

        self.title("Editar gasto" if gasto else "Nuevo gasto")
        self.geometry("380x520")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Concepto", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_concepto = ctk.CTkEntry(
            self, fg_color=theme.BG_INPUT, border_width=0, placeholder_text="Ej. Renta de agosto",
        )
        self.entry_concepto.pack(fill="x", padx=24, pady=(0, 12))
        if self.gasto:
            self.entry_concepto.insert(0, self.gasto.concepto)

        ctk.CTkLabel(self, text="Categoría", anchor="w").pack(fill="x", padx=24)
        valores = [gasto_service.CATEGORIA_ETIQUETAS[c] for c in gasto_service.CATEGORIAS]
        self.option_categoria = ctk.CTkOptionMenu(self, values=valores, fg_color=theme.BG_INPUT)
        self.option_categoria.pack(fill="x", padx=24, pady=(0, 12))
        if self.gasto:
            self.option_categoria.set(gasto_service.CATEGORIA_ETIQUETAS.get(self.gasto.categoria, valores[0]))

        ctk.CTkLabel(self, text="Monto ($)", anchor="w").pack(fill="x", padx=24)
        self.entry_monto = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_monto.pack(fill="x", padx=24, pady=(0, 12))
        if self.gasto:
            self.entry_monto.insert(0, str(self.gasto.monto))

        ctk.CTkLabel(self, text="Fecha (YYYY-MM-DD)", anchor="w").pack(fill="x", padx=24)
        self.entry_fecha = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_fecha.pack(fill="x", padx=24, pady=(0, 12))
        self.entry_fecha.insert(0, self.gasto.fecha if self.gasto else datetime.date.today().isoformat())

        ctk.CTkLabel(self, text="Notas (opcional)", anchor="w").pack(fill="x", padx=24)
        self.entry_notas = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_notas.pack(fill="x", padx=24, pady=(0, 12))
        if self.gasto and self.gasto.notas:
            self.entry_notas.insert(0, self.gasto.notas)

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=330, justify="left")
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, height=48,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24), side="bottom")

    def _categoria_seleccionada(self):
        etiqueta = self.option_categoria.get()
        for clave, valor in gasto_service.CATEGORIA_ETIQUETAS.items():
            if valor == etiqueta:
                return clave
        return gasto_service.CATEGORIAS[0]

    def _guardar(self):
        try:
            monto = float(self.entry_monto.get())
        except ValueError:
            self.label_error.configure(text="El monto debe ser un número")
            return

        concepto = self.entry_concepto.get()
        categoria = self._categoria_seleccionada()
        fecha = self.entry_fecha.get().strip()
        notas = self.entry_notas.get()

        try:
            if self.gasto:
                gasto_service.actualizar_gasto(self.gasto.id, concepto, categoria, monto, fecha, notas)
            else:
                gasto_service.crear_gasto(concepto, categoria, monto, fecha, self.current_user.id, notas)
        except gasto_service.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()


class ConfirmarEliminarGasto(ctk.CTkToplevel):
    def __init__(self, master, gasto, on_confirmado):
        super().__init__(master)
        self.gasto = gasto
        self.on_confirmado = on_confirmado

        self.title("Eliminar gasto")
        self.geometry("360x200")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f'¿Eliminar el gasto "{gasto.concepto}" (${gasto.monto:.2f})?',
            wraplength=310, justify="left",
        ).pack(fill="x", padx=24, pady=(24, 16))

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            botones, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Sí, eliminar", fg_color=theme.ERROR, hover_color=theme.ERROR,
            text_color="#FFFFFF", corner_radius=theme.RADIUS_BUTTON, command=self._eliminar,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _eliminar(self):
        gasto_service.eliminar_gasto(self.gasto.id)
        self.destroy()
        self.on_confirmado()
