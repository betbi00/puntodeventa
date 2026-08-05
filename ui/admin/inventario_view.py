"""Gestión de inventario: ingredientes, boba/perlas explosivas, bebidas y
productos base. Los cambios de stock siempre pasan por un "ajuste" con
motivo obligatorio (nunca se edita stock_actual directamente), y los
insumos/bebidas/productos solo se desactivan, nunca se eliminan."""
import customtkinter as ctk

from models import usuario as usuario_model
from services import inventario_service as inv
from ui import theme

UMBRAL_CONFIRMACION_PORCENTAJE = 0.5  # pedir confirmación si el ajuste reduce >= 50% del stock


class InventarioView(ctk.CTkFrame):
    def __init__(self, master, current_user):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Inventario", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", pady=(0, 16))

        tabview = ctk.CTkTabview(
            self, fg_color=theme.BG_CARD,
            segmented_button_fg_color=theme.BG_INPUT,
            segmented_button_selected_color=theme.PINK,
            segmented_button_selected_hover_color=theme.PINK_HOVER,
            segmented_button_unselected_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY,
        )
        tabview.pack(fill="both", expand=True)

        tab_ingredientes = tabview.add("Ingredientes")
        tab_extras = tabview.add("Boba y Perlas")
        tab_bebidas = tabview.add("Bebidas")
        tab_productos = tabview.add("Productos base")

        InsumosPanel(
            tab_ingredientes, tipos="ingrediente", tipo_nuevo="ingrediente",
            current_user=self.current_user, mostrar_precio_extra=True, mostrar_aplica_a=True,
            etiqueta_nuevo="+ Nuevo ingrediente",
        ).pack(fill="both", expand=True)

        InsumosPanel(
            tab_extras, tipos=["boba", "perla_explosiva"], tipo_nuevo=None,
            current_user=self.current_user, mostrar_precio_extra=False, mostrar_aplica_a=False,
            etiqueta_nuevo="+ Nuevo extra",
        ).pack(fill="both", expand=True)

        BebidasPanel(tab_bebidas).pack(fill="both", expand=True)
        ProductosBasePanel(tab_productos).pack(fill="both", expand=True)


# ---------------------------------------------------------------------------
# Insumos (ingredientes / boba / perlas explosivas)
# ---------------------------------------------------------------------------

class InsumosPanel(ctk.CTkFrame):
    def __init__(
        self, master, tipos, current_user, mostrar_precio_extra, mostrar_aplica_a,
        etiqueta_nuevo, tipo_nuevo=None,
    ):
        super().__init__(master, fg_color="transparent")
        self.tipos = tipos
        self.tipo_nuevo = tipo_nuevo
        self.current_user = current_user
        self.mostrar_precio_extra = mostrar_precio_extra
        self.mostrar_aplica_a = mostrar_aplica_a

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(12, 12))
        ctk.CTkButton(
            header, text=etiqueta_nuevo, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")

        self.lista_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.lista_frame.pack(fill="both", expand=True)

        self._refrescar()

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()
        for insumo in inv.listar_insumos(tipo=self.tipos):
            self._fila_insumo(insumo)

    def _fila_insumo(self, insumo):
        row = ctk.CTkFrame(self.lista_frame, fg_color="transparent")
        row.pack(fill="x", pady=8, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=insumo.nombre, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")

        detalle_partes = []
        if self.mostrar_precio_extra:
            detalle_partes.append(f"+${insumo.precio_extra:.2f}")
        else:
            detalle_partes.append("Sin costo extra")
        if self.mostrar_aplica_a:
            etiqueta_aplica = {"crepa": "Crepa", "waffle": "Waffle", "ambos": "Crepa y Waffle"}[insumo.aplica_a]
            detalle_partes.append(etiqueta_aplica)
        detalle_partes.append(f"Stock: {insumo.stock_actual:g} {insumo.unidad_medida} (mínimo {insumo.stock_minimo:g})")
        if not insumo.activo:
            detalle_partes.append("Inactivo")

        detalle = ctk.CTkFrame(info, fg_color="transparent")
        detalle.pack(anchor="w")
        color_stock = theme.ERROR if insumo.bajo_stock_minimo else theme.TEXT_SECONDARY
        for i, parte in enumerate(detalle_partes):
            es_stock = parte.startswith("Stock:")
            ctk.CTkLabel(
                detalle, text=parte + ("  ·  " if i < len(detalle_partes) - 1 else ""),
                text_color=color_stock if es_stock else theme.TEXT_SECONDARY,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold" if es_stock and insumo.bajo_stock_minimo else "normal"),
            ).pack(side="left")

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right")

        ctk.CTkButton(
            acciones, text="Ajustar stock", width=120, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BLUE_SOFT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
            command=lambda i=insumo: self._abrir_ajuste_stock(i),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            acciones, text="Historial", width=90, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda i=insumo: HistorialMovimientosView(self, i),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            acciones, text="Editar", width=80, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda i=insumo: self._abrir_form_editar(i),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            acciones, text=("Desactivar" if insumo.activo else "Activar"), width=100, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda i=insumo: self._toggle_activo(i),
        ).pack(side="left", padx=4)

    def _toggle_activo(self, insumo):
        inv.set_activo_insumo(insumo.id, not insumo.activo)
        self._refrescar()

    def _abrir_form_nuevo(self):
        tipos_permitidos = [self.tipo_nuevo] if self.tipo_nuevo else list(self.tipos)
        FormularioInsumo(self, tipos_permitidos=tipos_permitidos, insumo=None, on_guardado=self._refrescar)

    def _abrir_form_editar(self, insumo):
        FormularioInsumo(self, tipos_permitidos=[insumo.tipo], insumo=insumo, on_guardado=self._refrescar)

    def _abrir_ajuste_stock(self, insumo):
        FormularioAjusteStock(self, insumo, self.current_user, on_guardado=self._refrescar)


class FormularioInsumo(ctk.CTkToplevel):
    APLICA_A_OPCIONES = ["ambos", "crepa", "waffle"]
    TIPO_ETIQUETAS = {"ingrediente": "Ingrediente", "boba": "Boba", "perla_explosiva": "Perla explosiva"}

    def __init__(self, master, tipos_permitidos, insumo, on_guardado):
        super().__init__(master)
        self.es_edicion = insumo is not None
        self.insumo = insumo
        self.tipos_permitidos = tipos_permitidos
        self.on_guardado = on_guardado
        self.title("Editar insumo" if self.es_edicion else "Nuevo insumo")
        self.geometry("400x520")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24}

        ctk.CTkLabel(self, text="Nombre", anchor="w").pack(fill="x", pady=(24, 4), **pad)
        self.entry_nombre = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", pady=(0, 12), **pad)
        if self.es_edicion:
            self.entry_nombre.insert(0, self.insumo.nombre)

        mostrar_tipo = len(self.tipos_permitidos) > 1
        if mostrar_tipo:
            ctk.CTkLabel(self, text="Tipo", anchor="w").pack(fill="x", **pad)
            valores = [self.TIPO_ETIQUETAS[t] for t in self.tipos_permitidos]
            self.option_tipo = ctk.CTkOptionMenu(self, values=valores, fg_color=theme.BG_INPUT)
            self.option_tipo.pack(fill="x", pady=(0, 12), **pad)
        else:
            self.option_tipo = None

        self.tipo_fijo = self.tipos_permitidos[0] if not mostrar_tipo else None
        es_ingrediente = (self.tipo_fijo == "ingrediente") or (self.tipo_fijo is None and "ingrediente" in self.tipos_permitidos)

        if "ingrediente" in self.tipos_permitidos:
            ctk.CTkLabel(self, text="Aplica a", anchor="w").pack(fill="x", **pad)
            self.option_aplica_a = ctk.CTkOptionMenu(self, values=self.APLICA_A_OPCIONES, fg_color=theme.BG_INPUT)
            self.option_aplica_a.pack(fill="x", pady=(0, 12), **pad)
            if self.es_edicion:
                self.option_aplica_a.set(self.insumo.aplica_a)

            ctk.CTkLabel(self, text="Precio extra ($)", anchor="w").pack(fill="x", **pad)
            self.entry_precio = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
            self.entry_precio.pack(fill="x", pady=(0, 12), **pad)
            if self.es_edicion:
                self.entry_precio.insert(0, str(self.insumo.precio_extra))
        else:
            self.option_aplica_a = None
            self.entry_precio = None

        ctk.CTkLabel(self, text="Unidad de medida (ej. pza, g, ml, porcion)", anchor="w").pack(fill="x", **pad)
        self.entry_unidad = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_unidad.pack(fill="x", pady=(0, 12), **pad)
        self.entry_unidad.insert(0, self.insumo.unidad_medida if self.es_edicion else "pza")

        if not self.es_edicion:
            ctk.CTkLabel(self, text="Stock inicial", anchor="w").pack(fill="x", **pad)
            self.entry_stock_inicial = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
            self.entry_stock_inicial.pack(fill="x", pady=(0, 12), **pad)
            self.entry_stock_inicial.insert(0, "0")
        else:
            self.entry_stock_inicial = None

        ctk.CTkLabel(self, text="Stock mínimo (para alerta)", anchor="w").pack(fill="x", **pad)
        self.entry_stock_minimo = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_stock_minimo.pack(fill="x", pady=(0, 12), **pad)
        self.entry_stock_minimo.insert(0, str(self.insumo.stock_minimo) if self.es_edicion else "0")

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", **pad)

        ctk.CTkButton(
            self, text="Guardar" if self.es_edicion else "Crear insumo",
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            corner_radius=theme.RADIUS_BUTTON, command=self._guardar,
        ).pack(fill="x", pady=(12, 24), **pad)

    def _guardar(self):
        try:
            nombre = self.entry_nombre.get()
            aplica_a = self.option_aplica_a.get() if self.option_aplica_a else "ambos"
            precio_extra = float(self.entry_precio.get() or 0) if self.entry_precio else 0
            unidad = self.entry_unidad.get().strip() or "pza"
            stock_minimo = float(self.entry_stock_minimo.get() or 0)

            if self.es_edicion:
                inv.actualizar_insumo(self.insumo.id, nombre, aplica_a, precio_extra, unidad, stock_minimo)
            else:
                tipo = (
                    self.tipo_fijo
                    or self._tipo_desde_etiqueta(self.option_tipo.get())
                )
                stock_inicial = float(self.entry_stock_inicial.get() or 0)
                inv.crear_insumo(nombre, tipo, aplica_a, precio_extra, unidad, stock_inicial, stock_minimo)
        except (inv.ValidationError, ValueError) as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()

    def _tipo_desde_etiqueta(self, etiqueta):
        for tipo, label in self.TIPO_ETIQUETAS.items():
            if label == etiqueta:
                return tipo
        return etiqueta


class FormularioAjusteStock(ctk.CTkToplevel):
    def __init__(self, master, insumo, current_user, on_guardado):
        super().__init__(master)
        self.insumo = insumo
        self.current_user = current_user
        self.on_guardado = on_guardado
        self.title(f"Ajustar stock · {insumo.nombre}")
        self.geometry("380x360")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        pad = {"padx": 24}

        ctk.CTkLabel(
            self, text=f"Stock actual: {self.insumo.stock_actual:g} {self.insumo.unidad_medida}",
            anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(fill="x", pady=(24, 12), **pad)

        ctk.CTkLabel(self, text="Tipo de movimiento", anchor="w").pack(fill="x", **pad)
        self.option_tipo = ctk.CTkOptionMenu(
            self, values=["Entrada (llegó mercancía)", "Ajuste (corrección de conteo)"],
            fg_color=theme.BG_INPUT, command=self._on_tipo_changed,
        )
        self.option_tipo.pack(fill="x", pady=(0, 12), **pad)

        ctk.CTkLabel(self, text="Cantidad (usa negativo para restar)", anchor="w").pack(fill="x", **pad)
        self.entry_cantidad = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_cantidad.pack(fill="x", pady=(0, 12), **pad)

        self.label_motivo = ctk.CTkLabel(self, text="Motivo (obligatorio para ajustes)", anchor="w")
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

    def _on_tipo_changed(self, _valor):
        pass

    def _tipo_interno(self):
        return "entrada" if self.option_tipo.get().startswith("Entrada") else "ajuste"

    def _guardar(self, confirmado=False):
        try:
            cantidad = float(self.entry_cantidad.get())
        except ValueError:
            self.label_error.configure(text="La cantidad debe ser un número")
            return

        tipo = self._tipo_interno()
        motivo = self.entry_motivo.get().strip() or None

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
        self.geometry("360x220")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        mensaje = (
            f"Este ajuste dejará el stock de \"{insumo.nombre}\" en "
            f"{nuevo_stock:g} {insumo.unidad_medida} "
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
    def __init__(self, master, insumo):
        super().__init__(master)
        self.title(f"Historial de movimientos · {insumo.nombre}")
        self.geometry("520x420")
        self.configure(fg_color=theme.BG_PAGE)
        self._build(insumo)

    def _build(self, insumo):
        ctk.CTkLabel(
            self, text=insumo.nombre, font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self, text=f"Stock actual: {insumo.stock_actual:g} {insumo.unidad_medida}",
            text_color=theme.TEXT_SECONDARY,
        ).pack(anchor="w", padx=24, pady=(0, 16))

        lista = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        lista.pack(fill="both", expand=True, padx=24, pady=(0, 24))

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


# ---------------------------------------------------------------------------
# Bebidas
# ---------------------------------------------------------------------------

class BebidasPanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(12, 12))
        ctk.CTkButton(
            header, text="+ Nueva bebida", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")

        self.lista_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.lista_frame.pack(fill="both", expand=True)
        self._refrescar()

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()
        for bebida in inv.listar_bebidas():
            self._fila(bebida)

    def _fila(self, bebida):
        row = ctk.CTkFrame(self.lista_frame, fg_color="transparent")
        row.pack(fill="x", pady=8, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            info, text=bebida.nombre, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")
        subtitulo = f"${bebida.precio:.2f}" + ("" if bebida.activo else "  ·  Inactiva")
        ctk.CTkLabel(info, text=subtitulo, anchor="w", text_color=theme.TEXT_SECONDARY).pack(anchor="w")

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right")
        ctk.CTkButton(
            acciones, text="Editar", width=80, height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda b=bebida: FormularioBebida(self, b, on_guardado=self._refrescar),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            acciones, text=("Desactivar" if bebida.activo else "Activar"), width=100, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda b=bebida: self._toggle_activo(b),
        ).pack(side="left", padx=4)

    def _toggle_activo(self, bebida):
        inv.set_activo_bebida(bebida.id, not bebida.activo)
        self._refrescar()

    def _abrir_form_nuevo(self):
        FormularioBebida(self, None, on_guardado=self._refrescar)


class FormularioBebida(ctk.CTkToplevel):
    def __init__(self, master, bebida, on_guardado):
        super().__init__(master)
        self.bebida = bebida
        self.on_guardado = on_guardado
        self.title("Editar bebida" if bebida else "Nueva bebida")
        self.geometry("360x280")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Nombre", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_nombre = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))
        if self.bebida:
            self.entry_nombre.insert(0, self.bebida.nombre)

        ctk.CTkLabel(self, text="Precio ($)", anchor="w").pack(fill="x", padx=24)
        self.entry_precio = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_precio.pack(fill="x", padx=24, pady=(0, 12))
        if self.bebida:
            self.entry_precio.insert(0, str(self.bebida.precio))

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
            if self.bebida:
                inv.actualizar_bebida(self.bebida.id, self.entry_nombre.get(), precio)
            else:
                inv.crear_bebida(self.entry_nombre.get(), precio)
        except (inv.ValidationError, ValueError) as e:
            self.label_error.configure(text=str(e) if isinstance(e, inv.ValidationError) else "Precio inválido")
            return
        self.on_guardado()
        self.destroy()


# ---------------------------------------------------------------------------
# Productos base (Crepa, Waffle)
# ---------------------------------------------------------------------------

class ProductosBasePanel(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(12, 12))
        ctk.CTkButton(
            header, text="+ Nuevo producto base", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")

        self.lista_frame = ctk.CTkScrollableFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        self.lista_frame.pack(fill="both", expand=True)
        self._refrescar()

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()
        for producto in inv.listar_productos_base():
            self._fila(producto)

    def _fila(self, producto):
        row = ctk.CTkFrame(self.lista_frame, fg_color="transparent")
        row.pack(fill="x", pady=8, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            info, text=producto.nombre, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")
        subtitulo = f"Precio base: ${producto.precio_base:.2f}" + ("" if producto.activo else "  ·  Inactivo")
        ctk.CTkLabel(info, text=subtitulo, anchor="w", text_color=theme.TEXT_SECONDARY).pack(anchor="w")

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right")
        ctk.CTkButton(
            acciones, text="Editar", width=80, height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda p=producto: FormularioProductoBase(self, p, on_guardado=self._refrescar),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            acciones, text=("Desactivar" if producto.activo else "Activar"), width=100, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda p=producto: self._toggle_activo(p),
        ).pack(side="left", padx=4)

    def _toggle_activo(self, producto):
        inv.set_activo_producto_base(producto.id, not producto.activo)
        self._refrescar()

    def _abrir_form_nuevo(self):
        FormularioProductoBase(self, None, on_guardado=self._refrescar)


class FormularioProductoBase(ctk.CTkToplevel):
    def __init__(self, master, producto, on_guardado):
        super().__init__(master)
        self.producto = producto
        self.on_guardado = on_guardado
        self.title("Editar producto base" if producto else "Nuevo producto base")
        self.geometry("360x280")
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
