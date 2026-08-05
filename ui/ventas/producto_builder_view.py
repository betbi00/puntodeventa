"""Modal para armar una crepa/waffle personalizada: selecciona ingredientes
del inventario y ve el precio total y el desglose en tiempo real antes de
agregarlo a la venta.

Los ingredientes se muestran como tarjetas grandes en una cuadrícula (no
casillas pequeñas) pensadas para pantalla táctil: basta con tocar la
tarjeta para marcar/desmarcar el ingrediente.
"""
import customtkinter as ctk

from services import inventario_service as inv
from services import venta_service as vs
from ui import theme

COLUMNAS = 2


class ProductoBuilderView(ctk.CTkToplevel):
    def __init__(self, master, producto_base, on_agregar):
        super().__init__(master)
        self.producto_base = producto_base
        self.on_agregar = on_agregar
        self.seleccionados = set()
        self.tarjetas = {}  # insumo_id -> (CTkButton, Insumo)

        self.title(f"Armar {producto_base.nombre}")
        self.geometry("560x720")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text=self.producto_base.nombre,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 0))
        ctk.CTkLabel(
            self, text=f"Base: ${self.producto_base.precio_base:.2f}", text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            self, text="Ingredientes (toca para agregar)", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=24)

        grid_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD, height=340)
        grid_frame.pack(fill="both", expand=True, padx=24, pady=(8, 16))
        for columna in range(COLUMNAS):
            grid_frame.grid_columnconfigure(columna, weight=1)

        tipo_basico = self.producto_base.nombre.strip().lower()
        ingredientes = [
            i for i in inv.listar_insumos(tipo="ingrediente", incluir_inactivos=False)
            if i.aplica_a in ("ambos", tipo_basico)
        ]

        for index, insumo in enumerate(ingredientes):
            fila, columna = divmod(index, COLUMNAS)
            self._tarjeta_ingrediente(grid_frame, insumo, fila, columna)

        self.label_resumen = ctk.CTkLabel(
            self, text="Sin ingredientes agregados", text_color=theme.TEXT_SECONDARY,
            wraplength=380, justify="left",
        )
        self.label_resumen.pack(anchor="w", padx=24)

        self.label_total = ctk.CTkLabel(
            self, text=f"Total: ${self.producto_base.precio_base:.2f}",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        )
        self.label_total.pack(anchor="w", padx=24, pady=(4, 12))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=380, justify="left")
        self.label_error.pack(fill="x", padx=24)

        self.btn_agregar = ctk.CTkButton(
            self, text=f"Agregar ${self.producto_base.precio_base:.2f}",
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, height=52,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=self._agregar,
        )
        self.btn_agregar.pack(fill="x", padx=24, pady=(0, 24))

    def _tarjeta_ingrediente(self, master, insumo, fila, columna):
        agotado = insumo.stock_actual <= 0
        texto = f"{insumo.nombre}\n+${insumo.precio_extra:.2f}"
        if agotado:
            texto += "\nAgotado"
        boton = ctk.CTkButton(
            master, text=texto, height=84, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_PAGE, text_color=theme.TEXT_SECONDARY if agotado else theme.TEXT_PRIMARY,
            hover_color=theme.BG_PAGE if agotado else theme.BG_HOVER,
            state="disabled" if agotado else "normal",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=lambda i=insumo: self._toggle(i),
        )
        boton.grid(row=fila, column=columna, padx=8, pady=8, sticky="nsew")
        self.tarjetas[insumo.id] = (boton, insumo)

    def _toggle(self, insumo):
        if insumo.id in self.seleccionados:
            self.seleccionados.discard(insumo.id)
        else:
            self.seleccionados.add(insumo.id)
        self._refrescar_estilos()
        self._actualizar_resumen()

    def _refrescar_estilos(self):
        for insumo_id, (boton, insumo) in self.tarjetas.items():
            if insumo.stock_actual <= 0:
                continue
            if insumo_id in self.seleccionados:
                boton.configure(fg_color=theme.PINK, text_color=theme.TEXT_ON_ACCENT, hover_color=theme.PINK_HOVER)
            else:
                boton.configure(fg_color=theme.BG_PAGE, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER)

    def _actualizar_resumen(self):
        seleccionados = [insumo for (_b, insumo) in self.tarjetas.values() if insumo.id in self.seleccionados]
        total = self.producto_base.precio_base + sum(i.precio_extra for i in seleccionados)
        if seleccionados:
            self.label_resumen.configure(text="Ingredientes: " + ", ".join(i.nombre for i in seleccionados))
        else:
            self.label_resumen.configure(text="Sin ingredientes agregados")
        self.label_total.configure(text=f"Total: ${total:.2f}")
        self.btn_agregar.configure(text=f"Agregar ${total:.2f}")

    def _agregar(self):
        try:
            item = vs.armar_producto_base(self.producto_base.id, list(self.seleccionados))
        except vs.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_agregar(item)
        self.destroy()
