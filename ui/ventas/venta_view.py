"""Pantalla principal del punto de venta: catálogo (Crepas y Waffles en una
sola pantalla dividida, y Bebidas aparte) a la izquierda, carrito a la
derecha."""
import customtkinter as ctk

from services import impresion_service as imp
from services import inventario_service as inv
from services import venta_service as vs
from ui import theme
from ui.components.ticket_preview_view import TicketPreviewDialog
from ui.ventas.bebida_view import BebidaCatalogo
from ui.ventas.carrito_cobro_view import CarritoPanel
from ui.ventas.producto_builder_view import ProductoBuilderView

ICONOS_PRODUCTO_BASE = {"crepa": "🥞", "waffle": "🧇"}


class VentaView(ctk.CTkFrame):
    def __init__(self, master, current_user):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self.carrito = vs.Carrito()
        self._build()

    def _build(self):
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 16))

        tabview = ctk.CTkTabview(
            left, fg_color=theme.BG_CARD,
            segmented_button_fg_color=theme.BG_INPUT,
            segmented_button_selected_color=theme.PINK,
            segmented_button_selected_hover_color=theme.PINK_HOVER,
            segmented_button_unselected_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY,
        )
        tabview.pack(fill="both", expand=True)

        tab_productos = tabview.add("Crepas y Waffles")
        tab_bebidas = tabview.add("Bebidas")

        self._build_tab_productos_base(tab_productos)
        BebidaCatalogo(tab_bebidas, on_agregar=self._agregar_item).pack(fill="both", expand=True)

        self.carrito_panel = CarritoPanel(
            self, self.carrito, self.current_user, on_venta_completada=self._venta_completada,
        )
        self.carrito_panel.pack(side="right", fill="y")

    def _build_tab_productos_base(self, tab):
        """Una sola pantalla partida en dos mitades: Crepa a la izquierda,
        Waffle a la derecha. Tocar cualquiera abre el mismo constructor de
        siempre (ProductoBuilderView)."""
        container = ctk.CTkFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self._panel_producto_base(container, "Crepa", columna=0)
        self._panel_producto_base(container, "Waffle", columna=1)

    def _panel_producto_base(self, master, nombre_producto, columna):
        lado = ctk.CTkFrame(master, fg_color="transparent")
        lado.grid(row=0, column=columna, sticky="nsew", padx=12)

        ctk.CTkLabel(
            lado, text=nombre_producto.upper(), anchor="w", text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        card = ctk.CTkFrame(lado, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_CARD, cursor="hand2")
        card.pack(fill="both", expand=True)

        producto = next(
            (p for p in inv.listar_productos_base(incluir_inactivos=False)
             if p.nombre.strip().lower() == nombre_producto.lower()),
            None,
        )
        if producto is None:
            ctk.CTkLabel(
                card, text=f'No hay un producto base configurado para "{nombre_producto}". '
                          "Agrégalo en Inventario.",
                text_color=theme.TEXT_SECONDARY, wraplength=280, justify="center",
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        contenido = ctk.CTkFrame(card, fg_color="transparent")
        contenido.place(relx=0.5, rely=0.5, anchor="center")

        icono = ICONOS_PRODUCTO_BASE.get(nombre_producto.lower(), "🍽️")
        ctk.CTkLabel(contenido, text=icono, font=(theme.FONT_FAMILY, 56)).pack(pady=(0, 12))
        ctk.CTkLabel(
            contenido, text=f"Armar {producto.nombre}", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack()
        ctk.CTkLabel(
            contenido, text=f"Desde ${producto.precio_base:.2f}", text_color=theme.TEXT_SECONDARY,
        ).pack(pady=(4, 0))

        def abrir(_evento=None, p=producto):
            ProductoBuilderView(self, p, on_agregar=self._agregar_item)

        card.bind("<Button-1>", abrir)
        contenido.bind("<Button-1>", abrir)
        for child in contenido.winfo_children():
            child.bind("<Button-1>", abrir)

    def _agregar_item(self, item):
        self.carrito.agregar(item)
        self.carrito_panel.refrescar()

    def _venta_completada(self, venta_id):
        """La venta ya quedó registrada en la base de datos en este punto.
        Intentamos imprimir el ticket automáticamente; si la impresora
        falla o no está conectada, el diálogo lo avisa y ofrece
        reintentar, pero la venta sigue registrada de cualquier forma."""
        datos_ticket = imp.datos_ticket_de_venta(venta_id)
        TicketPreviewDialog(self, datos_ticket, venta_id=venta_id, intentar_imprimir_automaticamente=True)
