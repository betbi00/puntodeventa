"""Gestión de inventario: ingredientes, boba/perlas explosivas/pulpa,
bebidas y productos base, todo en una sola vista con buscador y filtro por
categoría. Los cambios de stock siempre pasan por un "ajuste" con motivo
obligatorio (nunca se edita stock_actual directamente). Un insumo, bebida o
producto base solo se puede eliminar de verdad si nunca se ha vendido ni
tiene movimientos de stock registrados; en cualquier otro caso se protege
y solo se puede desactivar."""
import tkinter as tk

import customtkinter as ctk

from models import usuario as usuario_model
from services import inventario_service as inv
from ui import theme
from ui.components.scroll_tactil import habilitar_scroll_tactil
from ui.components.ventana_emergente import ajustar_geometria

UMBRAL_CONFIRMACION_PORCENTAJE = 0.5  # pedir confirmación si el ajuste reduce >= 50% del stock

CATEGORIA_ARMADO_ETIQUETAS = {
    "base": "Base", "fruta": "Fruta", "complemento": "Complemento", "decoracion": "Decoración",
}
CATEGORIA_ARMADO_OPCIONES = ["(Ninguna)"] + list(CATEGORIA_ARMADO_ETIQUETAS.values())

TIPO_EXTRA_ETIQUETAS = {"boba_perlas": "Boba / Perlas explosivas (varias a la vez)", "pulpa": "Pulpa de fruta (una sola)"}
TIPO_EXTRA_OPCIONES = ["(Ninguno)"] + list(TIPO_EXTRA_ETIQUETAS.values())

# Grupo al que pertenece cada fila de la vista unificada: controla el
# badge que se muestra y las opciones del filtro por categoría.
GRUPO_ETIQUETAS = {
    "ingrediente": "Ingrediente",
    "extra": "Extra de bebida",
    "bebida": "Bebida",
    "desechable": "Desechable",
    "producto_base": "Producto base",
}
GRUPOS_FILTRO = ["Todos"] + list(GRUPO_ETIQUETAS.values())

# CTkOptionMenu por defecto usa el azul/gris del tema base de customtkinter
# (no la paleta rosa de Cuillas) y un text_color pensado para modo oscuro,
# lo que lo deja casi ilegible sobre nuestros fondos claros — se fuerzan
# aquí los mismos colores que ya usa el resto de la app.
ESTILO_OPTION_MENU = dict(
    fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
    button_color=theme.BG_INPUT, button_hover_color=theme.BG_HOVER,
    dropdown_fg_color=theme.BG_CARD, dropdown_text_color=theme.TEXT_PRIMARY,
    dropdown_hover_color=theme.BG_HOVER,
)


class InventarioView(ctk.CTkFrame):
    def __init__(self, master, current_user, puede_editar=None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self.puede_editar = puede_editar if puede_editar is not None else (current_user.rol == "admin")
        self.filtro_texto = ""
        self.filtro_grupo = "Todos"
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Inventario", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", pady=(0, 16))

        if not self.puede_editar:
            ctk.CTkLabel(
                self, text="Puedes registrar entradas de mercancía y ajustar stock. "
                           "Crear, editar o eliminar artículos solo lo puede hacer un administrador.",
                text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
                wraplength=600, justify="left",
            ).pack(anchor="w", pady=(0, 12))

        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, 12))

        self.entry_buscar = ctk.CTkEntry(
            barra, placeholder_text="Buscar por nombre...", fg_color=theme.BG_INPUT, border_width=0,
        )
        self.entry_buscar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.entry_buscar.bind("<KeyRelease>", lambda _e: self._on_filtro_cambiado())

        grupos_disponibles = (
            GRUPOS_FILTRO if self.puede_editar
            else [g for g in GRUPOS_FILTRO if g != GRUPO_ETIQUETAS["producto_base"]]
        )
        self.option_grupo = ctk.CTkOptionMenu(
            barra, values=grupos_disponibles, **ESTILO_OPTION_MENU,
            command=lambda _v: self._on_filtro_cambiado(),
        )
        self.option_grupo.set("Todos")
        self.option_grupo.pack(side="left", padx=(0, 8))

        if self.puede_editar:
            self.btn_nuevo = ctk.CTkButton(
                barra, text="+ Nuevo", corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
                command=self._abrir_menu_nuevo,
            )
            self.btn_nuevo.pack(side="left")

        self.lista_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.lista_frame.pack(fill="both", expand=True)

        self._refrescar()

    # -- filtro / búsqueda ---------------------------------------------------

    def _on_filtro_cambiado(self):
        self.filtro_texto = self.entry_buscar.get().strip().lower()
        self.filtro_grupo = self.option_grupo.get()
        self._refrescar()

    def _abrir_menu_nuevo(self):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Ingrediente", command=lambda: self._abrir_form_nuevo_insumo("ingrediente"))
        menu.add_command(label="Boba", command=lambda: self._abrir_form_nuevo_insumo("boba"))
        menu.add_command(label="Perla explosiva", command=lambda: self._abrir_form_nuevo_insumo("perla_explosiva"))
        menu.add_command(label="Pulpa de fruta", command=lambda: self._abrir_form_nuevo_insumo("pulpa"))
        menu.add_command(label="Desechable", command=lambda: self._abrir_form_nuevo_insumo("desechable"))
        menu.add_separator()
        menu.add_command(label="Bebida", command=self._abrir_form_nuevo_bebida)
        menu.add_command(label="Producto base (Crepa/Waffle)", command=self._abrir_form_nuevo_producto_base)
        menu.tk_popup(self.btn_nuevo.winfo_rootx(), self.btn_nuevo.winfo_rooty() + self.btn_nuevo.winfo_height())

    def _abrir_form_nuevo_insumo(self, tipo):
        FormularioInsumo(self, tipos_permitidos=[tipo], insumo=None, on_guardado=self._refrescar)

    def _abrir_form_nuevo_bebida(self):
        FormularioBebida(self, None, on_guardado=self._refrescar)

    def _abrir_form_nuevo_producto_base(self):
        FormularioProductoBase(self, None, on_guardado=self._refrescar)

    # -- listado --------------------------------------------------------------

    def _recolectar_items(self):
        """[(grupo, objeto)] con todo lo que el rol actual puede ver, ya
        filtrado por texto/categoría y ordenado por nombre."""
        items = []
        for insumo in inv.listar_insumos(tipo="ingrediente"):
            items.append(("ingrediente", insumo))
        for insumo in inv.listar_insumos(tipo=["boba", "perla_explosiva", "pulpa"]):
            items.append(("extra", insumo))
        for insumo in inv.listar_insumos(tipo="desechable"):
            items.append(("desechable", insumo))
        for bebida in inv.listar_bebidas():
            items.append(("bebida", bebida))
        # El precio base de Crepa/Waffle es exclusivo del administrador: el
        # vendedor ni siquiera ve que existe (mismo criterio que antes).
        if self.puede_editar:
            for producto in inv.listar_productos_base():
                items.append(("producto_base", producto))

        if self.filtro_grupo != "Todos":
            grupo_seleccionado = next(g for g, etiqueta in GRUPO_ETIQUETAS.items() if etiqueta == self.filtro_grupo)
            items = [(g, o) for (g, o) in items if g == grupo_seleccionado]

        if self.filtro_texto:
            items = [(g, o) for (g, o) in items if self.filtro_texto in o.nombre.lower()]

        items.sort(key=lambda go: go[1].nombre.lower())
        return items

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()
        items = self._recolectar_items()
        if not items:
            ctk.CTkLabel(
                self.lista_frame, text="No se encontró nada con ese filtro.", text_color=theme.TEXT_SECONDARY,
            ).pack(pady=16)
            return
        for grupo, objeto in items:
            self._fila(grupo, objeto)
        habilitar_scroll_tactil(self.lista_frame)

    def _fila(self, grupo, objeto):
        row = ctk.CTkFrame(self.lista_frame, fg_color="transparent")
        row.pack(fill="x", pady=3, padx=6)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        encabezado = ctk.CTkFrame(info, fg_color="transparent")
        encabezado.pack(anchor="w", fill="x")
        ctk.CTkLabel(
            encabezado, text=objeto.nombre, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")
        badge = ctk.CTkFrame(encabezado, fg_color=theme.BG_INPUT, corner_radius=theme.RADIUS_BUTTON)
        badge.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(
            badge, text=GRUPO_ETIQUETAS[grupo], text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(padx=8, pady=1)

        # El vendedor solo ve nombre + badge + Ajustar stock — nada de
        # precio, cantidades de stock ni acciones de edición/eliminación
        # (los productos base ni llegan aquí, ver _recolectar_items).
        if not self.puede_editar:
            acciones = ctk.CTkFrame(row, fg_color="transparent")
            acciones.pack(side="right")
            ctk.CTkButton(
                acciones, text="Ajustar Stock", width=160, height=44,
                corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BLUE_SOFT,
                text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
                command=lambda g=grupo, o=objeto: self._abrir_ajuste_stock(g, o),
            ).pack(side="left", padx=4)
            return

        detalle = ctk.CTkFrame(info, fg_color="transparent")
        detalle.pack(anchor="w")
        partes = self._detalle_partes(grupo, objeto)
        for i, (texto, es_alerta) in enumerate(partes):
            ctk.CTkLabel(
                detalle, text=texto + ("  ·  " if i < len(partes) - 1 else ""),
                text_color=theme.ERROR if es_alerta else theme.TEXT_SECONDARY,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold" if es_alerta else "normal"),
            ).pack(side="left")

        # Se usa grid (no pack) con un ancho fijo por columna: así "Editar"
        # y "Desactivar" siempre caen en la misma posición en todas las
        # filas, sin importar si esa fila en particular tiene "Ajustar
        # Stock" (no aplica a producto_base) o "Eliminar" (no aplica si ya
        # tiene historial) — con pack, cada fila con menos botones
        # "flotaba" hacia la izquierda de forma distinta y quedaba
        # desalineada con el resto.
        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right")
        for columna, ancho in enumerate((168, 118, 148, 128)):
            acciones.grid_columnconfigure(columna, minsize=ancho)

        if grupo != "producto_base":
            ctk.CTkButton(
                acciones, text="Ajustar Stock", width=160, height=44,
                corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BLUE_SOFT,
                text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
                command=lambda g=grupo, o=objeto: self._abrir_ajuste_stock(g, o),
            ).grid(row=0, column=0, padx=4)

        ctk.CTkButton(
            acciones, text="Editar", width=110, height=44,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=lambda g=grupo, o=objeto: self._abrir_form_editar(g, o),
        ).grid(row=0, column=1, padx=4)

        # Activar/Desactivar y Eliminar son independientes entre sí: un
        # artículo sin historial se puede eliminar de verdad, pero eso no
        # debe quitarle la forma de activarlo/desactivarlo (por ejemplo,
        # una bebida nueva que todavía no se ha vendido sigue necesitando
        # poder activarse para poder venderla).
        ctk.CTkButton(
            acciones, text=("Desactivar" if objeto.activo else "Activar"), width=140, height=44,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            command=lambda g=grupo, o=objeto: self._toggle_activo(g, o),
        ).grid(row=0, column=2, padx=4)

        if self._puede_eliminarse(grupo, objeto):
            ctk.CTkButton(
                acciones, text="Eliminar", width=120, height=44,
                corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
                text_color=theme.ERROR, hover_color=theme.BG_HOVER,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
                command=lambda g=grupo, o=objeto: self._confirmar_eliminar(g, o),
            ).grid(row=0, column=3, padx=4)

    def _detalle_partes(self, grupo, objeto):
        """[(texto, es_alerta)] con el detalle de una fila según su tipo."""
        partes = []
        if grupo == "producto_base":
            partes.append((f"Precio base: ${objeto.precio_base:.2f}", False))
        elif grupo == "bebida":
            partes.append((f"${objeto.precio:.2f}", False))
            partes.append((f"Stock: {objeto.stock_actual:g} (mínimo {objeto.stock_minimo:g})", objeto.bajo_stock_minimo))
        else:  # ingrediente, extra, desechable -> Insumo
            if grupo == "ingrediente":
                partes.append((f"+${objeto.precio_extra:.2f}", False))
                etiqueta_aplica = {"crepa": "Crepa", "waffle": "Waffle", "ambos": "Crepa y Waffle"}[objeto.aplica_a]
                partes.append((etiqueta_aplica, False))
                if objeto.categoria_armado:
                    partes.append((CATEGORIA_ARMADO_ETIQUETAS[objeto.categoria_armado], False))
            else:
                partes.append(("Sin costo extra", False))
            partes.append((
                f"Stock: {objeto.stock_actual:g} {objeto.unidad_medida} (mínimo {objeto.stock_minimo:g})",
                objeto.bajo_stock_minimo,
            ))
        if not objeto.activo:
            partes.append(("Inactiva" if grupo == "bebida" else "Inactivo", False))
        return partes

    def _puede_eliminarse(self, grupo, objeto):
        if grupo == "producto_base":
            return inv.producto_base_puede_eliminarse(objeto.id)
        if grupo == "bebida":
            return inv.bebida_puede_eliminarse(objeto.id)
        return inv.insumo_puede_eliminarse(objeto.id)

    def _toggle_activo(self, grupo, objeto):
        if grupo == "producto_base":
            inv.set_activo_producto_base(objeto.id, not objeto.activo)
        elif grupo == "bebida":
            inv.set_activo_bebida(objeto.id, not objeto.activo)
        else:
            inv.set_activo_insumo(objeto.id, not objeto.activo)
        self._refrescar()

    def _confirmar_eliminar(self, grupo, objeto):
        ConfirmarEliminar(self, objeto.nombre, on_confirmar=lambda: self._eliminar(grupo, objeto))

    def _eliminar(self, grupo, objeto):
        try:
            if grupo == "producto_base":
                inv.eliminar_producto_base(objeto.id)
            elif grupo == "bebida":
                inv.eliminar_bebida(objeto.id)
            else:
                inv.eliminar_insumo(objeto.id)
        except inv.ValidationError:
            pass  # se volvió a usar justo antes de confirmar: se refresca y queda protegido con Desactivar
        self._refrescar()

    def _abrir_form_editar(self, grupo, objeto):
        if grupo == "producto_base":
            FormularioProductoBase(self, objeto, on_guardado=self._refrescar)
        elif grupo == "bebida":
            FormularioBebida(self, objeto, on_guardado=self._refrescar)
        else:
            FormularioInsumo(self, tipos_permitidos=[objeto.tipo], insumo=objeto, on_guardado=self._refrescar)

    def _abrir_ajuste_stock(self, grupo, objeto):
        FormularioAjusteStock(
            self, objeto, self.current_user, on_guardado=self._refrescar,
            solo_entrada=not self.puede_editar, entidad_tipo="bebida" if grupo == "bebida" else "insumo",
        )


class ConfirmarEliminar(ctk.CTkToplevel):
    def __init__(self, master, nombre, on_confirmar):
        super().__init__(master)
        self.on_confirmar = on_confirmar
        self.title("Eliminar")
        ajustar_geometria(self, 360, 220)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        mensaje = (
            f"¿Eliminar \"{nombre}\" definitivamente?\n\n"
            "Esta acción no se puede deshacer. Solo se puede hacer porque "
            "nunca se ha vendido ni tiene movimientos de stock registrados."
        )
        ctk.CTkLabel(self, text=mensaje, wraplength=310, justify="left").pack(
            fill="x", padx=24, pady=(24, 16)
        )

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            botones, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Sí, eliminar", fg_color=theme.ERROR, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._confirmar,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _confirmar(self):
        self.destroy()
        self.on_confirmar()


class FormularioInsumo(ctk.CTkToplevel):
    APLICA_A_OPCIONES = ["ambos", "crepa", "waffle"]
    TIPO_ETIQUETAS = {
        "ingrediente": "Ingrediente", "boba": "Boba", "perla_explosiva": "Perla explosiva",
        "desechable": "Desechable", "pulpa": "Pulpa de fruta",
    }

    def __init__(self, master, tipos_permitidos, insumo, on_guardado):
        super().__init__(master)
        self.es_edicion = insumo is not None
        self.insumo = insumo
        self.tipos_permitidos = tipos_permitidos
        self.on_guardado = on_guardado
        self.title("Editar insumo" if self.es_edicion else "Nuevo insumo")
        ajustar_geometria(self, 480, 560)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24}

        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, pady=(16, 0))

        ctk.CTkLabel(contenido, text="Nombre", anchor="w").pack(fill="x", pady=(8, 4), **pad)
        self.entry_nombre = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", pady=(0, 12), **pad)
        if self.es_edicion:
            self.entry_nombre.insert(0, self.insumo.nombre)

        mostrar_tipo = len(self.tipos_permitidos) > 1
        if mostrar_tipo:
            ctk.CTkLabel(contenido, text="Tipo", anchor="w").pack(fill="x", **pad)
            valores = [self.TIPO_ETIQUETAS[t] for t in self.tipos_permitidos]
            self.option_tipo = ctk.CTkOptionMenu(contenido, values=valores, **ESTILO_OPTION_MENU)
            self.option_tipo.pack(fill="x", pady=(0, 12), **pad)
        else:
            self.option_tipo = None

        self.tipo_fijo = self.tipos_permitidos[0] if not mostrar_tipo else None

        # El precio se puede ajustar para cualquier tipo de insumo (antes
        # solo aparecía para ingredientes) — para poder cobrar, por
        # ejemplo, un extra de boba/perla o un desechable que hoy es
        # gratis pero mañana no.
        ctk.CTkLabel(contenido, text="Precio extra ($)", anchor="w").pack(fill="x", **pad)
        self.entry_precio = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_precio.pack(fill="x", pady=(0, 12), **pad)
        self.entry_precio.insert(0, str(self.insumo.precio_extra) if self.es_edicion else "0")

        if "ingrediente" in self.tipos_permitidos:
            ctk.CTkLabel(contenido, text="Aplica a", anchor="w").pack(fill="x", **pad)
            self.option_aplica_a = ctk.CTkOptionMenu(contenido, values=self.APLICA_A_OPCIONES, **ESTILO_OPTION_MENU)
            self.option_aplica_a.pack(fill="x", pady=(0, 12), **pad)
            if self.es_edicion:
                self.option_aplica_a.set(self.insumo.aplica_a)

            ctk.CTkLabel(
                contenido, text="Categoría en el armador de Crepa/Waffle (opcional)", anchor="w",
            ).pack(fill="x", **pad)
            self.option_categoria_armado = ctk.CTkOptionMenu(
                contenido, values=CATEGORIA_ARMADO_OPCIONES, **ESTILO_OPTION_MENU,
            )
            self.option_categoria_armado.pack(fill="x", pady=(0, 12), **pad)
            if self.es_edicion and self.insumo.categoria_armado:
                self.option_categoria_armado.set(CATEGORIA_ARMADO_ETIQUETAS[self.insumo.categoria_armado])
        else:
            self.option_aplica_a = None
            self.option_categoria_armado = None

        ctk.CTkLabel(contenido, text="Unidad de medida (ej. pza, g, ml, porcion)", anchor="w").pack(fill="x", **pad)
        self.entry_unidad = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_unidad.pack(fill="x", pady=(0, 12), **pad)
        self.entry_unidad.insert(0, self.insumo.unidad_medida if self.es_edicion else "pza")

        if not self.es_edicion:
            ctk.CTkLabel(contenido, text="Stock inicial", anchor="w").pack(fill="x", **pad)
            self.entry_stock_inicial = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
            self.entry_stock_inicial.pack(fill="x", pady=(0, 12), **pad)
            self.entry_stock_inicial.insert(0, "0")
        else:
            self.entry_stock_inicial = None

        ctk.CTkLabel(contenido, text="Stock mínimo (para alerta)", anchor="w").pack(fill="x", **pad)
        self.entry_stock_minimo = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_stock_minimo.pack(fill="x", pady=(0, 12), **pad)
        self.entry_stock_minimo.insert(0, str(self.insumo.stock_minimo) if self.es_edicion else "0")

        self.label_error = ctk.CTkLabel(contenido, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", **pad)

        ctk.CTkButton(
            self, text="Guardar" if self.es_edicion else "Crear insumo",
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            corner_radius=theme.RADIUS_BUTTON, command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 16), side="bottom")

        habilitar_scroll_tactil(contenido)

    def _guardar(self):
        try:
            nombre = self.entry_nombre.get()
            aplica_a = self.option_aplica_a.get() if self.option_aplica_a else "ambos"
            precio_extra = float(self.entry_precio.get() or 0)
            unidad = self.entry_unidad.get().strip() or "pza"
            stock_minimo = float(self.entry_stock_minimo.get() or 0)
            categoria_armado = self._categoria_armado_seleccionada()

            if self.es_edicion:
                inv.actualizar_insumo(
                    self.insumo.id, nombre, aplica_a, precio_extra, unidad, stock_minimo, categoria_armado,
                )
            else:
                tipo = (
                    self.tipo_fijo
                    or self._tipo_desde_etiqueta(self.option_tipo.get())
                )
                stock_inicial = float(self.entry_stock_inicial.get() or 0)
                inv.crear_insumo(
                    nombre, tipo, aplica_a, precio_extra, unidad, stock_inicial, stock_minimo, categoria_armado,
                )
        except (inv.ValidationError, ValueError) as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()

    def _categoria_armado_seleccionada(self):
        if not self.option_categoria_armado:
            return None
        etiqueta = self.option_categoria_armado.get()
        for valor, label in CATEGORIA_ARMADO_ETIQUETAS.items():
            if label == etiqueta:
                return valor
        return None

    def _tipo_desde_etiqueta(self, etiqueta):
        for tipo, label in self.TIPO_ETIQUETAS.items():
            if label == etiqueta:
                return tipo
        return etiqueta


class FormularioAjusteStock(ctk.CTkToplevel):
    def __init__(self, master, insumo, current_user, on_guardado, solo_entrada=False, entidad_tipo="insumo"):
        super().__init__(master)
        self.insumo = insumo
        self.current_user = current_user
        self.on_guardado = on_guardado
        # entidad_tipo distingue si esta entidad es un insumo o una bebida,
        # porque cada una vive en su propia tabla con su propio servicio de
        # ajuste de stock — el resto del formulario es idéntico para ambas.
        self.entidad_tipo = entidad_tipo
        self.unidad = getattr(insumo, "unidad_medida", "pza")
        # Para quien no puede ver cifras de stock (vendedor): solo se le
        # permite registrar una Entrada (siempre positiva), nunca un Ajuste
        # — un ajuste requiere comparar contra el stock actual, que no ve.
        self.solo_entrada = solo_entrada
        self.title(f"Ajustar stock · {insumo.nombre}")
        ajustar_geometria(self, 380, 320 if solo_entrada else 360)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24}

        if not self.solo_entrada:
            ctk.CTkLabel(
                self, text=f"Stock actual: {self.insumo.stock_actual:g} {self.unidad}",
                anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            ).pack(fill="x", pady=(24, 12), **pad)

        if self.solo_entrada:
            self.option_tipo = None
            ctk.CTkLabel(
                self, text="Vas a registrar una entrada (mercancía que llegó de un proveedor).",
                text_color=theme.TEXT_SECONDARY, wraplength=330, justify="left",
            ).pack(fill="x", pady=(24, 12), **pad)
            ctk.CTkLabel(self, text="Cantidad recibida", anchor="w").pack(fill="x", **pad)
        else:
            ctk.CTkLabel(self, text="Tipo de movimiento", anchor="w").pack(fill="x", **pad)
            self.option_tipo = ctk.CTkOptionMenu(
                self, values=["Entrada (llegó mercancía)", "Ajuste (corrección de conteo)"],
                **ESTILO_OPTION_MENU,
            )
            self.option_tipo.pack(fill="x", pady=(0, 12), **pad)
            ctk.CTkLabel(self, text="Cantidad (usa negativo para restar)", anchor="w").pack(fill="x", **pad)

        self.entry_cantidad = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_cantidad.pack(fill="x", pady=(0, 12), **pad)

        self.label_motivo = ctk.CTkLabel(
            self, text="Nota (opcional)" if self.solo_entrada else "Motivo (obligatorio para ajustes)", anchor="w",
        )
        self.label_motivo.pack(fill="x", **pad)
        self.entry_motivo = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_motivo.pack(fill="x", pady=(0, 12), **pad)

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=330, justify="left")
        self.label_error.pack(fill="x", **pad)

        ctk.CTkButton(
            self, text="Guardar movimiento", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._guardar,
        ).pack(fill="x", pady=(12, 24), **pad)

    def _tipo_interno(self):
        if self.solo_entrada:
            return "entrada"
        return "entrada" if self.option_tipo.get().startswith("Entrada") else "ajuste"

    def _guardar(self, confirmado=False):
        try:
            cantidad = float(self.entry_cantidad.get())
        except ValueError:
            self.label_error.configure(text="La cantidad debe ser un número")
            return

        if self.solo_entrada and cantidad <= 0:
            self.label_error.configure(text="La cantidad recibida debe ser mayor a cero")
            return

        tipo = self._tipo_interno()
        motivo = self.entry_motivo.get().strip() or None

        if not self.solo_entrada:
            nuevo_stock_estimado = self.insumo.stock_actual + cantidad
            reduccion_grande = (
                cantidad < 0
                and self.insumo.stock_actual > 0
                and abs(cantidad) >= self.insumo.stock_actual * UMBRAL_CONFIRMACION_PORCENTAJE
            )
            if reduccion_grande and not confirmado:
                ConfirmacionAjusteGrande(
                    self, self.insumo, nuevo_stock_estimado,
                    on_confirmar=lambda: self._guardar(confirmado=True),
                )
                return

        try:
            if self.entidad_tipo == "bebida":
                inv.ajustar_stock_bebida(
                    self.insumo.id, tipo, cantidad, usuario_id=self.current_user.id, motivo=motivo,
                )
            else:
                inv.ajustar_stock(
                    self.insumo.id, tipo, cantidad, usuario_id=self.current_user.id, motivo=motivo,
                )
        except inv.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()


class ConfirmacionAjusteGrande(ctk.CTkToplevel):
    def __init__(self, master, insumo, nuevo_stock, on_confirmar):
        super().__init__(master)
        self.on_confirmar = on_confirmar
        self.title("Confirmar ajuste")
        ajustar_geometria(self, 360, 220)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        unidad = getattr(insumo, "unidad_medida", "pza")
        mensaje = (
            f"Este ajuste dejará el stock de \"{insumo.nombre}\" en "
            f"{nuevo_stock:g} {unidad} "
            f"(actualmente hay {insumo.stock_actual:g}).\n\n¿Confirmas el ajuste?"
        )
        ctk.CTkLabel(self, text=mensaje, wraplength=310, justify="left").pack(
            fill="x", padx=24, pady=(24, 16)
        )

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            botones, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Sí, confirmar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._confirmar,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _confirmar(self):
        self.destroy()
        self.on_confirmar()


class HistorialMovimientosView(ctk.CTkToplevel):
    def __init__(self, master, insumo, entidad_tipo="insumo"):
        super().__init__(master)
        self.entidad_tipo = entidad_tipo
        self.title(f"Historial de movimientos · {insumo.nombre}")
        ajustar_geometria(self, 520, 420)
        self.configure(fg_color=theme.BG_PAGE)
        self._build(insumo)

    def _build(self, insumo):
        unidad = getattr(insumo, "unidad_medida", "pza")
        ctk.CTkLabel(
            self, text=insumo.nombre, font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, text=f"Stock actual: {insumo.stock_actual:g} {unidad}",
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        lista = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        lista.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        if self.entidad_tipo == "bebida":
            movimientos = inv.historial_movimientos_bebida(insumo.id)
        else:
            movimientos = inv.historial_movimientos(insumo.id)
        if not movimientos:
            ctk.CTkLabel(lista, text="Sin movimientos registrados todavía.", text_color=theme.TEXT_SECONDARY).pack(
                pady=16
            )
            return

        for m in movimientos:
            usuario = usuario_model.get_by_id(m.usuario_id)
            nombre_usuario = usuario.nombre if usuario else f"Usuario #{m.usuario_id}"
            fila = ctk.CTkFrame(lista, fg_color="transparent")
            fila.pack(fill="x", pady=6, padx=8)

            signo = "+" if m.cantidad > 0 else ""
            tipo_label = {"entrada": "Entrada", "ajuste": "Ajuste", "venta": "Venta"}.get(m.tipo, m.tipo)
            ctk.CTkLabel(
                fila, text=f"{tipo_label}: {signo}{m.cantidad:g} → stock {m.stock_resultante:g}",
                anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            ).pack(anchor="w")
            detalle = f"{m.fecha_hora} · {nombre_usuario}"
            if m.motivo:
                detalle += f" · {m.motivo}"
            ctk.CTkLabel(
                fila, text=detalle, anchor="w", text_color=theme.TEXT_SECONDARY,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            ).pack(anchor="w")

        habilitar_scroll_tactil(lista)


class FormularioBebida(ctk.CTkToplevel):
    def __init__(self, master, bebida, on_guardado):
        super().__init__(master)
        self.bebida = bebida
        self.on_guardado = on_guardado
        self.title("Editar bebida" if bebida else "Nueva bebida")
        ajustar_geometria(self, 420, 480)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, pady=(16, 0))

        ctk.CTkLabel(contenido, text="Nombre", anchor="w").pack(fill="x", padx=24, pady=(8, 4))
        self.entry_nombre = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))
        if self.bebida:
            self.entry_nombre.insert(0, self.bebida.nombre)

        ctk.CTkLabel(contenido, text="Precio ($)", anchor="w").pack(fill="x", padx=24)
        self.entry_precio = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_precio.pack(fill="x", padx=24, pady=(0, 12))
        if self.bebida:
            self.entry_precio.insert(0, str(self.bebida.precio))

        ctk.CTkLabel(contenido, text="Extra que se ofrece al vender (opcional)", anchor="w").pack(fill="x", padx=24)
        self.option_tipo_extra = ctk.CTkOptionMenu(contenido, values=TIPO_EXTRA_OPCIONES, **ESTILO_OPTION_MENU)
        self.option_tipo_extra.pack(fill="x", padx=24, pady=(0, 12))
        if self.bebida and self.bebida.tipo_extra:
            self.option_tipo_extra.set(TIPO_EXTRA_ETIQUETAS[self.bebida.tipo_extra])

        if not self.bebida:
            ctk.CTkLabel(contenido, text="Stock inicial", anchor="w").pack(fill="x", padx=24)
            self.entry_stock_inicial = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
            self.entry_stock_inicial.pack(fill="x", padx=24, pady=(0, 12))
            self.entry_stock_inicial.insert(0, "0")
        else:
            self.entry_stock_inicial = None

        ctk.CTkLabel(contenido, text="Stock mínimo (para alerta)", anchor="w").pack(fill="x", padx=24)
        self.entry_stock_minimo = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_stock_minimo.pack(fill="x", padx=24, pady=(0, 12))
        self.entry_stock_minimo.insert(0, str(self.bebida.stock_minimo) if self.bebida else "0")

        self.label_error = ctk.CTkLabel(contenido, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 16), side="bottom")

        habilitar_scroll_tactil(contenido)

    def _guardar(self):
        try:
            precio = float(self.entry_precio.get())
            stock_minimo = float(self.entry_stock_minimo.get() or 0)
            tipo_extra = self._tipo_extra_seleccionado()
            if self.bebida:
                inv.actualizar_bebida(self.bebida.id, self.entry_nombre.get(), precio, stock_minimo, tipo_extra)
            else:
                stock_inicial = float(self.entry_stock_inicial.get() or 0)
                inv.crear_bebida(self.entry_nombre.get(), precio, stock_inicial, stock_minimo, tipo_extra)
        except (inv.ValidationError, ValueError) as e:
            self.label_error.configure(text=str(e) if isinstance(e, inv.ValidationError) else "Precio o stock inválido")
            return
        self.on_guardado()
        self.destroy()

    def _tipo_extra_seleccionado(self):
        etiqueta = self.option_tipo_extra.get()
        for valor, label in TIPO_EXTRA_ETIQUETAS.items():
            if label == etiqueta:
                return valor
        return None


class FormularioProductoBase(ctk.CTkToplevel):
    def __init__(self, master, producto, on_guardado):
        super().__init__(master)
        self.producto = producto
        self.on_guardado = on_guardado
        self.title("Editar producto base" if producto else "Nuevo producto base")
        ajustar_geometria(self, 360, 280)
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Nombre (ej. Crepa, Waffle)", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_nombre = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))
        if self.producto:
            self.entry_nombre.insert(0, self.producto.nombre)

        ctk.CTkLabel(self, text="Precio base ($)", anchor="w").pack(fill="x", padx=24)
        self.entry_precio = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_precio.pack(fill="x", padx=24, pady=(0, 12))
        if self.producto:
            self.entry_precio.insert(0, str(self.producto.precio_base))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24))

    def _guardar(self):
        try:
            precio = float(self.entry_precio.get())
            if self.producto:
                inv.actualizar_producto_base(self.producto.id, self.entry_nombre.get(), precio)
            else:
                inv.crear_producto_base(self.entry_nombre.get(), precio)
        except (inv.ValidationError, ValueError) as e:
            self.label_error.configure(text=str(e) if isinstance(e, inv.ValidationError) else "Precio inválido")
            return
        self.on_guardado()
        self.destroy()
