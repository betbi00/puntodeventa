"""Vista previa del ticket que se va a imprimir (o que ya se intentó
imprimir). Si la impresora falla o no está conectada, se muestra el motivo
y se ofrece reintentar — la venta ya registrada nunca se ve afectada por
esto."""
import customtkinter as ctk

from services import impresion_service as imp
from ui import theme


class TicketPreviewDialog(ctk.CTkToplevel):
    def __init__(self, master, datos_ticket, venta_id=None, intentar_imprimir_automaticamente=False):
        super().__init__(master)
        self.datos_ticket = datos_ticket
        self.venta_id = venta_id

        titulo = "Vista previa del ticket" if venta_id is None else f"Ticket · Venta #{venta_id}"
        self.title(titulo)
        self.geometry("440x680")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

        if intentar_imprimir_automaticamente:
            self._imprimir()

    def _build(self):
        ctk.CTkLabel(
            self, text="Vista previa del ticket", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 8))

        caja = ctk.CTkTextbox(
            self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD,
            font=("Courier New", 12), wrap="none",
        )
        caja.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        caja.insert("1.0", imp.renderizar_texto(self.datos_ticket))
        caja.configure(state="disabled")

        self.label_estado = ctk.CTkLabel(self, text="", wraplength=390, justify="left")
        self.label_estado.pack(fill="x", padx=20)

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=20, pady=(8, 20))
        self.btn_imprimir = ctk.CTkButton(
            botones, text="🖨️  Imprimir", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, command=self._imprimir,
        )
        self.btn_imprimir.pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Cerrar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _imprimir(self):
        self.btn_imprimir.configure(text="Imprimiendo…", state="disabled")
        self.update_idletasks()
        try:
            if self.venta_id is not None:
                imp.imprimir_venta(self.venta_id)
            else:
                imp.imprimir(self.datos_ticket)
        except imp.ImpresionError as e:
            self.label_estado.configure(
                text=f"⚠️ No se pudo imprimir: {e}\n\n"
                     "La venta ya está registrada — puedes reintentar cuando quieras.",
                text_color=theme.ERROR,
            )
            self.btn_imprimir.configure(text="Reintentar impresión", state="normal")
            return
        self.label_estado.configure(text="✅ Ticket enviado a la impresora correctamente.", text_color=theme.SUCCESS)
        self.btn_imprimir.configure(text="Imprimir de nuevo", state="normal")
