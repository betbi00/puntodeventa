"""Modal para armar una crepa/waffle personalizada, siguiendo el flujo
guiado del menú oficial: Base → Fruta → Complemento opcional →
Decoración, en ese orden. Ve el precio total y el desglose en tiempo
real antes de agregarlo a la venta.

Pensado para pantalla táctil sin mouse: la ventana es apaisada (más
ancha que alta) en vez de una lista larga que obliga a hacer scroll
para llegar al botón de agregar — "Agregar" vive en un panel fijo a la
derecha que siempre se ve completo, sin importar cuántos ingredientes
haya ni cuánto se haga scroll en la lista de la izquierda.

Los ingredientes se muestran como tarjetas grandes en una cuadrícula (no
casillas pequeñas): basta con tocar la tarjeta para marcar/desmarcar el
ingrediente. Se puede combinar más de uno en cualquier paso (por
ejemplo Nutella y queso crema/Philadelphia juntos en "Base") — no hay
ningún paso de elección única.
"""
import customtkinter as ctk

from services import inventario_service as inv
from services import venta_service as vs
from ui import theme
from ui.components.scroll_tactil import habilitar_scroll_tactil
from ui.components.ventana_emergente import ajustar_geometria

COLUMNAS = 3
ANCHO_PANEL_DERECHO = 250

# (categoria_armado, título de la sección)
PASOS_ARMADO = [
    ("base", "1. Elige tu base"),
    ("fruta", "2. Elige tu fruta"),
    ("complemento", "3. Complemento opcional"),
    ("decoracion", "4. Decoración"),
]


class ProductoBuilderView(ctk.CTkToplevel):
    def __init__(self, master, producto_base, on_agregar):
        super().__init__(master)
        self.producto_base = producto_base
        self.on_agregar = on_agregar
        self.seleccionados = set()
        self.tarjetas = {}  # insumo_id -> (CTkButton, Insumo)
        self.categoria_por_insumo = {}  # insumo_id -> categoria_armado

        self.title(f"Armar {producto_base.nombre}")
        ajustar_geometria(self, 820, 480)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self._build()
        # grab_set() antes de que la ventana termine de dibujarse puede dejarla
        # con tamaño roto e invisible en macOS: como ya tiene el grab modal,
        # ningún clic llega a ninguna ventana y la app entera parece
        # congelada. update_idletasks() fuerza a que la geometría ya esté
        # aplicada antes de pedir el grab.
        self.update_idletasks()
        self.after(10, self.grab_set)

    def _build(self):
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=16, pady=16)

        izquierda = ctk.CTkFrame(cuerpo, fg_color="transparent")
        izquierda.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ctk.CTkLabel(
            izquierda, text=self.producto_base.nombre,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        contenido = ctk.CTkScrollableFrame(izquierda, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        contenido.pack(fill="both", expand=True)

        tipo_basico = self.producto_base.nombre.strip().lower()
        ingredientes = [
            i for i in inv.listar_insumos(tipo="ingrediente", incluir_inactivos=False)
            if i.aplica_a in ("ambos", tipo_basico)
        ]
        por_categoria = {}
        for insumo in ingredientes:
            if insumo.categoria_armado:
                por_categoria.setdefault(insumo.categoria_armado, []).append(insumo)
                self.categoria_por_insumo[insumo.id] = insumo.categoria_armado

        self.hay_base_disponible = bool(por_categoria.get("base"))

        for categoria, titulo in PASOS_ARMADO:
            items = por_categoria.get(categoria)
            if not items:
                continue  # sin ingredientes en este paso todavía: no se muestra
            ctk.CTkLabel(
                contenido, text=titulo, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            ).pack(anchor="w", padx=8, pady=(10, 4))
            grid_frame = ctk.CTkFrame(contenido, fg_color="transparent")
            grid_frame.pack(fill="x", padx=8, pady=(0, 4))
            for columna in range(COLUMNAS):
                grid_frame.grid_columnconfigure(columna, weight=1)
            for index, insumo in enumerate(items):
                fila, columna = divmod(index, COLUMNAS)
                self._tarjeta_ingrediente(grid_frame, insumo, fila, columna)

        derecha = ctk.CTkFrame(
            cuerpo, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD, width=ANCHO_PANEL_DERECHO,
        )
        derecha.pack(side="right", fill="y")
        derecha.pack_propagate(False)

        ctk.CTkLabel(
            derecha, text=f"Base: ${self.producto_base.precio_base:.2f}", anchor="w",
            text_color=theme.TEXT_SECONDARY,
        ).pack(fill="x", padx=16, pady=(16, 8))

        self.label_resumen = ctk.CTkLabel(
            derecha, text="Sin ingredientes agregados", text_color=theme.TEXT_SECONDARY,
            wraplength=ANCHO_PANEL_DERECHO - 32, justify="left", anchor="w",
        )
        self.label_resumen.pack(fill="x", padx=16)

        self.label_total = ctk.CTkLabel(
            derecha, text=f"Total: ${self.producto_base.precio_base:.2f}", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        )
        self.label_total.pack(fill="x", padx=16, pady=(8, 8))

        self.label_error = ctk.CTkLabel(
            derecha, text="", text_color=theme.ERROR,
            wraplength=ANCHO_PANEL_DERECHO - 32, justify="left", anchor="w",
        )
        self.label_error.pack(fill="x", padx=16)

        self.btn_agregar = ctk.CTkButton(
            derecha, text=f"Agregar ${self.producto_base.precio_base:.2f}",
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, height=56,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=self._agregar,
        )
        self.btn_agregar.pack(fill="x", padx=16, pady=16, side="bottom")

        habilitar_scroll_tactil(contenido)

    def _tarjeta_ingrediente(self, master, insumo, fila, columna):
        agotado = insumo.stock_actual <= 0
        texto = f"{insumo.nombre}\n+${insumo.precio_extra:.2f}"
        if agotado:
            texto += "\nAgotado"
        boton = ctk.CTkButton(
            master, text=texto, height=76, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_PAGE, text_color=theme.TEXT_SECONDARY if agotado else theme.TEXT_PRIMARY,
            hover_color=theme.BG_PAGE if agotado else theme.BG_HOVER,
            state="disabled" if agotado else "normal",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=lambda i=insumo: self._toggle(i),
        )
        boton.grid(row=fila, column=columna, padx=6, pady=6, sticky="nsew")
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

    def _tiene_base_seleccionada(self) -> bool:
        return any(self.categoria_por_insumo.get(i) == "base" for i in self.seleccionados)

    def _agregar(self):
        if self.hay_base_disponible and not self._tiene_base_seleccionada():
            self.label_error.configure(text="Elige una base antes de continuar")
            return
        try:
            item = vs.armar_producto_base(self.producto_base.id, list(self.seleccionados))
        except vs.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_agregar(item)
        self.destroy()
