"""Panel del carrito de venta (lista de productos agregados y total) y el
diálogo de cobro (descuento, quién cobra y método de pago)."""
import customtkinter as ctk

from models import usuario as usuario_model
from services import mercadopago_service as mp
from services import promocion_service as promos
from services import venta_service as vs
from ui import theme
from ui.ventas.pago_tarjeta_view import PagoTarjetaDialog

COLUMNAS_USUARIOS = 3
DESCUENTOS_GENERALES = [10, 15, 20, 25]


class CarritoPanel(ctk.CTkFrame):
    def __init__(self, master, carrito, current_user, on_venta_completada=None):
        super().__init__(master, fg_color=theme.BG_CARD, width=340, corner_radius=theme.RADIUS_CARD)
        self.pack_propagate(False)
        self.carrito = carrito
        self.current_user = current_user
        self.on_venta_completada = on_venta_completada
        self._build()
        self.refrescar()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header, text="Venta actual", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")
        self.badge_count = ctk.CTkLabel(
            header, text="0", fg_color=theme.PINK_SOFT, text_color=theme.TEXT_PRIMARY,
            corner_radius=10, width=24, height=24, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold"),
        )
        self.badge_count.pack(side="right")

        self.items_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.items_frame.pack(fill="both", expand=True, padx=8)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=16, side="bottom")

        self.label_subtotal = ctk.CTkLabel(bottom, text="Subtotal: $0.00", anchor="w", text_color=theme.TEXT_SECONDARY)
        self.label_subtotal.pack(fill="x")

        total_row = ctk.CTkFrame(bottom, fg_color="transparent")
        total_row.pack(fill="x", pady=(8, 12))
        ctk.CTkLabel(
            total_row, text="Total", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")
        self.label_total = ctk.CTkLabel(
            total_row, text="$0.00", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        )
        self.label_total.pack(side="right")

        self.btn_cobrar = ctk.CTkButton(
            bottom, text="Cobrar  →", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            height=44, command=self._abrir_cobro,
        )
        self.btn_cobrar.pack(fill="x")

    def refrescar(self):
        for widget in self.items_frame.winfo_children():
            widget.destroy()
        for idx, item in enumerate(self.carrito.items):
            self._fila_item(idx, item)
        self.badge_count.configure(text=str(len(self.carrito.items)))
        self._actualizar_totales()

    def _fila_item(self, idx, item):
        row = ctk.CTkFrame(self.items_frame, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_INPUT)
        row.pack(fill="x", pady=4, padx=4)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ctk.CTkLabel(
            info, text=item.nombre_producto, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")
        if item.descripcion_insumos:
            ctk.CTkLabel(
                info, text=item.descripcion_insumos, anchor="w", text_color=theme.TEXT_SECONDARY,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            ).pack(anchor="w")
        ctk.CTkLabel(info, text=f"${item.subtotal:.2f}", anchor="w", text_color=theme.PINK_HOVER).pack(anchor="w")

        ctk.CTkButton(
            row, text="Eliminar", width=70, height=24, fg_color="transparent",
            text_color=theme.ERROR, hover_color=theme.BG_HOVER,
            command=lambda i=idx: self._eliminar(i),
        ).pack(side="right", padx=8)

    def _eliminar(self, idx):
        self.carrito.eliminar(idx)
        self.refrescar()

    def _actualizar_totales(self):
        subtotal = self.carrito.subtotal
        self.label_subtotal.configure(text=f"Subtotal: ${subtotal:.2f}")
        self.label_total.configure(text=f"${subtotal:.2f}")
        self.btn_cobrar.configure(state="disabled" if self.carrito.esta_vacio else "normal")

    def _abrir_cobro(self):
        if self.carrito.esta_vacio:
            return
        CobroDialog(self, self.carrito, self.current_user, on_completada=self._venta_completada)

    def _venta_completada(self, venta_id):
        self.carrito.vaciar()
        self.refrescar()
        if self.on_venta_completada:
            self.on_venta_completada(venta_id)


class CobroDialog(ctk.CTkToplevel):
    def __init__(self, master, carrito, current_user, on_completada):
        super().__init__(master)
        self.carrito = carrito
        self.current_user = current_user
        self.on_completada = on_completada
        self.metodo_seleccionado = "efectivo"
        self.usuario_seleccionado_id = current_user.id
        self.promocion_seleccionada_id = None
        self.botones_usuario = {}  # usuario_id -> CTkButton
        self.botones_promocion = {}  # promocion_id -> CTkButton

        self.title("Confirmar cobro")
        self.geometry("420x820")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Confirmar cobro", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(anchor="w", padx=24, pady=(24, 12))

        resumen = ctk.CTkFrame(self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        resumen.pack(fill="x", padx=24)

        fila_subtotal = ctk.CTkFrame(resumen, fg_color="transparent")
        fila_subtotal.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(fila_subtotal, text="Subtotal", text_color=theme.TEXT_SECONDARY).pack(side="left")
        self.label_subtotal = ctk.CTkLabel(
            fila_subtotal, text=f"${self.carrito.subtotal:.2f}", text_color=theme.TEXT_SECONDARY,
        )
        self.label_subtotal.pack(side="right")

        fila_descuento = ctk.CTkFrame(resumen, fg_color="transparent")
        fila_descuento.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(fila_descuento, text="% Descuento", text_color=theme.TEXT_SECONDARY).pack(side="left")
        self.entry_descuento = ctk.CTkEntry(
            fila_descuento, width=70, fg_color=theme.BG_INPUT, border_width=0, justify="right",
        )
        self.entry_descuento.insert(0, "0")
        self.entry_descuento.pack(side="right")
        self.entry_descuento.bind("<KeyRelease>", lambda _e: self._descuento_editado_manualmente())

        fila_descuento_monto = ctk.CTkFrame(resumen, fg_color="transparent")
        fila_descuento_monto.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(fila_descuento_monto, text="Descuento aplicado", text_color=theme.TEXT_SECONDARY).pack(side="left")
        self.label_descuento_monto = ctk.CTkLabel(fila_descuento_monto, text="-$0.00", text_color=theme.TEXT_SECONDARY)
        self.label_descuento_monto.pack(side="right")

        total_row = ctk.CTkFrame(resumen, fg_color="transparent")
        total_row.pack(fill="x", padx=16, pady=(4, 16))
        ctk.CTkLabel(total_row, text="Total", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold")).pack(side="left")
        self.label_total = ctk.CTkLabel(
            total_row, text=f"${self.carrito.subtotal:.2f}", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        )
        self.label_total.pack(side="right")

        ctk.CTkLabel(self, text="Descuentos rápidos", anchor="w").pack(fill="x", padx=24, pady=(16, 4))
        generales_frame = ctk.CTkFrame(self, fg_color="transparent")
        generales_frame.pack(fill="x", padx=24)
        for pct in DESCUENTOS_GENERALES:
            ctk.CTkButton(
                generales_frame, text=f"{pct}%", width=56, height=32, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
                command=lambda p=pct: self._elegir_descuento_general(p),
            ).pack(side="left", padx=(0, 4))

        promociones_activas = promos.listar_promociones(incluir_inactivas=False)
        if promociones_activas:
            ctk.CTkLabel(self, text="Promociones", anchor="w").pack(fill="x", padx=24, pady=(12, 4))
            promos_frame = ctk.CTkFrame(self, fg_color="transparent")
            promos_frame.pack(fill="x", padx=24)
            for promo in promociones_activas:
                boton = ctk.CTkButton(
                    promos_frame, text=f"{promo.nombre} ({promo.porcentaje:g}%)", height=32,
                    corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BLUE_SOFT,
                    text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
                    command=lambda p=promo: self._elegir_promocion(p),
                )
                boton.pack(side="left", padx=(0, 4), pady=2)
                self.botones_promocion[promo.id] = boton

        ctk.CTkLabel(self, text="¿Quién cobra?", anchor="w").pack(fill="x", padx=24, pady=(16, 4))
        usuarios_frame = ctk.CTkFrame(self, fg_color="transparent")
        usuarios_frame.pack(fill="x", padx=24)
        for columna in range(COLUMNAS_USUARIOS):
            usuarios_frame.grid_columnconfigure(columna, weight=1)

        usuarios_activos = usuario_model.listar(incluir_inactivos=False)
        for index, usuario in enumerate(usuarios_activos):
            fila, columna = divmod(index, COLUMNAS_USUARIOS)
            boton = ctk.CTkButton(
                usuarios_frame, text=usuario.nombre, height=40, corner_radius=theme.RADIUS_BUTTON,
                command=lambda u=usuario: self._elegir_usuario(u.id),
            )
            boton.grid(row=fila, column=columna, padx=4, pady=4, sticky="nsew")
            self.botones_usuario[usuario.id] = boton

        ctk.CTkLabel(self, text="Método de pago", anchor="w").pack(fill="x", padx=24, pady=(16, 4))
        metodo_row = ctk.CTkFrame(self, fg_color="transparent")
        metodo_row.pack(fill="x", padx=24)
        self.btn_efectivo = ctk.CTkButton(
            metodo_row, text="Efectivo", corner_radius=theme.RADIUS_BUTTON,
            command=lambda: self._elegir_metodo("efectivo"),
        )
        self.btn_efectivo.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_tarjeta = ctk.CTkButton(
            metodo_row, text="Tarjeta", corner_radius=theme.RADIUS_BUTTON,
            command=lambda: self._elegir_metodo("tarjeta"),
        )
        self.btn_tarjeta.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.label_nota = ctk.CTkLabel(
            self, text="", text_color=theme.TEXT_SECONDARY, wraplength=350, justify="left",
        )
        self.label_nota.pack(fill="x", padx=24, pady=(8, 0))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=350, justify="left")
        self.label_error.pack(fill="x", padx=24, pady=(4, 0))

        ctk.CTkButton(
            self, text="Confirmar venta", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, height=48,
            command=self._confirmar,
        ).pack(fill="x", padx=24, pady=(16, 24), side="bottom")

        self._elegir_usuario(self.current_user.id)
        self._elegir_metodo("efectivo")

    def _obtener_descuento_pct(self):
        try:
            valor = float(self.entry_descuento.get() or 0)
        except ValueError:
            return 0
        return max(0, min(100, valor))

    def _actualizar_totales(self):
        descuento_pct = self._obtener_descuento_pct()
        descuento_monto, total = self.carrito.calcular_descuento_y_total(descuento_pct)
        self.label_descuento_monto.configure(text=f"-${descuento_monto:.2f}")
        self.label_total.configure(text=f"${total:.2f}")

    def _descuento_editado_manualmente(self):
        # Escribir directamente en el campo siempre se toma como un
        # descuento manual: se suelta cualquier promoción seleccionada.
        self._deseleccionar_promocion()
        self._actualizar_totales()

    def _elegir_descuento_general(self, pct):
        self._deseleccionar_promocion()
        self.entry_descuento.delete(0, "end")
        self.entry_descuento.insert(0, str(pct))
        self._actualizar_totales()

    def _elegir_promocion(self, promo):
        self.entry_descuento.delete(0, "end")
        self.entry_descuento.insert(0, f"{promo.porcentaje:g}")
        self.promocion_seleccionada_id = promo.id
        for pid, boton in self.botones_promocion.items():
            if pid == promo.id:
                boton.configure(fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT)
            else:
                boton.configure(fg_color=theme.BLUE_SOFT, hover_color=theme.BLUE, text_color=theme.TEXT_PRIMARY)
        self._actualizar_totales()

    def _deseleccionar_promocion(self):
        self.promocion_seleccionada_id = None
        for boton in self.botones_promocion.values():
            boton.configure(fg_color=theme.BLUE_SOFT, hover_color=theme.BLUE, text_color=theme.TEXT_PRIMARY)

    def _elegir_usuario(self, usuario_id):
        self.usuario_seleccionado_id = usuario_id
        for uid, boton in self.botones_usuario.items():
            if uid == usuario_id:
                boton.configure(fg_color=theme.PINK, text_color=theme.TEXT_ON_ACCENT, hover_color=theme.PINK_HOVER)
            else:
                boton.configure(fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER)

    def _elegir_metodo(self, metodo):
        self.metodo_seleccionado = metodo
        activo = {"fg_color": theme.PINK, "text_color": theme.TEXT_ON_ACCENT, "hover_color": theme.PINK_HOVER}
        inactivo = {"fg_color": theme.BG_INPUT, "text_color": theme.TEXT_PRIMARY, "hover_color": theme.BG_HOVER}
        self.btn_efectivo.configure(**(activo if metodo == "efectivo" else inactivo))
        self.btn_tarjeta.configure(**(activo if metodo == "tarjeta" else inactivo))
        if metodo == "tarjeta":
            if not mp.esta_configurado():
                nota = ("Mercado Pago aún no está configurado — se usará un simulador de "
                        "terminal para poder probar el cobro con tarjeta.")
            elif mp.modo_sandbox():
                nota = "Modo sandbox: se usará tu cuenta de prueba de Mercado Pago."
            else:
                nota = "Modo producción: se cobrará de verdad en tu terminal Mercado Pago Point."
            self.label_nota.configure(text=nota)
        else:
            self.label_nota.configure(text="")

    def _confirmar(self):
        self.label_error.configure(text="")
        descuento_pct = self._obtener_descuento_pct()

        if self.metodo_seleccionado == "tarjeta":
            _, total = self.carrito.calcular_descuento_y_total(descuento_pct)
            PagoTarjetaDialog(
                self, total,
                on_resultado=lambda *resultado: self._resultado_pago_tarjeta(descuento_pct, *resultado),
            )
            return

        self._registrar_venta(descuento_pct, "efectivo")

    def _resultado_pago_tarjeta(self, descuento_pct, aprobado, payment_id, status, mensaje):
        if not aprobado:
            # Pago rechazado, cancelado o con error: la venta NO se registra.
            # El diálogo de cobro sigue abierto para reintentar o cambiar a efectivo.
            self.label_error.configure(text=mensaje)
            return
        self._registrar_venta(descuento_pct, "tarjeta", mp_payment_id=payment_id, mp_status=status)

    def _registrar_venta(self, descuento_pct, metodo_pago, mp_payment_id=None, mp_status=None):
        try:
            venta_id = vs.registrar_venta(
                self.carrito, usuario_id=self.usuario_seleccionado_id, descuento_pct=descuento_pct,
                metodo_pago=metodo_pago, mp_payment_id=mp_payment_id, mp_status=mp_status,
                promocion_id=self.promocion_seleccionada_id,
            )
        except vs.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.destroy()
        self.on_completada(venta_id)
