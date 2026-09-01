"""Diálogo de cobro con tarjeta: si Mercado Pago está configurado, envía
el cobro a la terminal Point real y espera la confirmación; si no, usa un
simulador de terminal para poder probar el flujo completo de
aprobar/rechazar sin cuenta ni hardware real todavía."""
import uuid

import customtkinter as ctk

from services import mercadopago_service as mp
from ui import theme

INTERVALO_POLL_MS = 2000
MAX_INTENTOS = 150  # ~5 minutos, en línea con el expiration_time de la orden


class PagoTarjetaDialog(ctk.CTkToplevel):
    def __init__(self, master, monto, on_resultado):
        """on_resultado(aprobado, mp_payment_id, mp_status, mensaje) se
        llama exactamente una vez, con el resultado final o la
        cancelación."""
        super().__init__(master)
        self.monto = monto
        self.on_resultado = on_resultado
        self._resuelto = False
        self._order_id = None
        self._intentos = 0

        self.title("Cobro con tarjeta")
        self.geometry("380x340")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        if mp.esta_configurado():
            self._build_real()
        else:
            self._build_simulador()

        # Igual que en CobroDialog: pedir el grab antes de que la ventana
        # termine de dibujarse puede dejarla con tamaño roto e invisible en
        # macOS, congelando la app entera porque el grab modal ya está
        # activo en una ventana con la que no se puede interactuar.
        self.update_idletasks()
        self.after(10, self.grab_set)

    # --- Modo real: Mercado Pago Point configurado ---
    def _build_real(self):
        etiqueta_modo = "Modo sandbox" if mp.modo_sandbox() else "Modo producción"
        ctk.CTkLabel(self, text=etiqueta_modo, text_color=theme.TEXT_SECONDARY).pack(pady=(20, 4))
        ctk.CTkLabel(
            self, text=f"Cobrando ${self.monto:.2f}", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(pady=(0, 16))

        self.label_estado = ctk.CTkLabel(
            self, text="Enviando a la terminal…", wraplength=320, justify="center",
        )
        self.label_estado.pack(padx=20, pady=(0, 16))

        ctk.CTkButton(
            self, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self._cancelar,
        ).pack(side="bottom", fill="x", padx=20, pady=20)

        try:
            referencia = f"pos-{uuid.uuid4()}"
            orden = mp.crear_orden_pago(self.monto, referencia)
        except mp.MercadoPagoError as e:
            self._finalizar(False, None, None, str(e))
            return

        self._order_id = orden.get("id")
        self.label_estado.configure(text="Esperando a que el cliente pague en la terminal…")
        self.after(INTERVALO_POLL_MS, self._consultar_estado)

    def _consultar_estado(self):
        if self._resuelto:
            return
        self._intentos += 1
        try:
            orden = mp.consultar_orden(self._order_id)
        except mp.MercadoPagoError as e:
            self._finalizar(False, None, None, str(e))
            return

        estado, payment_id = mp.extraer_resultado(orden)
        if estado in mp.ESTADOS_APROBADOS:
            self._finalizar(True, payment_id, estado, "Pago aprobado")
        elif estado in mp.ESTADOS_RECHAZADOS:
            self._finalizar(False, payment_id, estado, f"Pago no completado ({estado})")
        elif self._intentos >= MAX_INTENTOS:
            self._finalizar(False, None, "timeout", "Se agotó el tiempo de espera de la terminal")
        else:
            self.after(INTERVALO_POLL_MS, self._consultar_estado)

    # --- Modo simulador: todavía no hay credenciales de Mercado Pago ---
    def _build_simulador(self):
        ctk.CTkLabel(
            self, text="MODO SIMULADO", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            text_color=theme.ERROR,
        ).pack(pady=(20, 4))
        ctk.CTkLabel(
            self, text="Mercado Pago aún no está configurado (falta el Access Token y/o el "
                       "terminal_id en el archivo .env). Usa estos botones solo para probar "
                       "el flujo mientras tanto.",
            text_color=theme.TEXT_SECONDARY, wraplength=320, justify="center",
        ).pack(padx=20, pady=(0, 16))
        ctk.CTkLabel(
            self, text=f"Cobrando ${self.monto:.2f}", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(pady=(0, 16))

        ctk.CTkButton(
            self, text="Simular pago APROBADO", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=lambda: self._finalizar(
                True, f"SIMULADO-{uuid.uuid4().hex[:8]}", "processed", "Pago aprobado (simulado)"
            ),
        ).pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(
            self, text="Simular pago RECHAZADO", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda: self._finalizar(False, None, "failed", "Pago rechazado (simulado)"),
        ).pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkButton(
            self, text="Cancelar", fg_color="transparent", text_color=theme.TEXT_SECONDARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self._cancelar,
        ).pack(fill="x", padx=20)

    def _finalizar(self, aprobado, payment_id, status, mensaje):
        if self._resuelto:
            return
        self._resuelto = True
        # Igual que en CobroDialog: diferir la continuación evita que en
        # macOS se abra otro diálogo modal en el mismo instante en que este
        # se destruye, lo cual deja el grab en un estado inconsistente y
        # congela la app.
        master = self.master
        self.grab_release()
        self.destroy()
        master.after(50, lambda: self.on_resultado(aprobado, payment_id, status, mensaje))

    def _cancelar(self):
        if self._resuelto:
            return
        self._resuelto = True
        if self._order_id:
            mp.cancelar_orden(self._order_id)
        master = self.master
        self.grab_release()
        self.destroy()
        master.after(50, lambda: self.on_resultado(False, None, "canceled_by_user", "Cobro cancelado"))
