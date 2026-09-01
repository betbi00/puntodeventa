"""Vista previa del ticket (y de la comanda, si aplica) que se van a
imprimir, o que ya se intentaron imprimir. Si la impresora falla o no
está conectada, se muestra el motivo y se ofrece reintentar — la venta ya
registrada nunca se ve afectada por esto.

Cuando hay comanda, cada trabajo de impresión (ticket / comanda) se
rastrea por separado: un reintento solo repite el que falló, nunca
reimprime físicamente el que ya salió bien."""
import customtkinter as ctk

from services import impresion_service as imp
from ui import theme


class TicketPreviewDialog(ctk.CTkToplevel):
    def __init__(
        self, master, datos_ticket, datos_comanda=None, venta_id=None,
        intentar_imprimir_automaticamente=False,
    ):
        super().__init__(master)
        self.datos_ticket = datos_ticket
        self.datos_comanda = datos_comanda
        self.venta_id = venta_id
        self._ticket_ok = False
        self._comanda_ok = not bool(datos_comanda)

        titulo = "Vista previa del ticket" if venta_id is None else f"Ticket · Venta #{venta_id}"
        self.title(titulo)
        self.geometry("760x680" if datos_comanda else "440x680")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self._build()
        # Igual que en CobroDialog: pedir el grab antes de que la ventana
        # termine de dibujarse puede dejarla con tamaño roto e invisible en
        # macOS, congelando la app entera porque el grab modal ya está
        # activo en una ventana con la que no se puede interactuar.
        self.update_idletasks()
        self.after(10, self.grab_set)

        if intentar_imprimir_automaticamente:
            self._imprimir()

    def _build(self):
        cajas_frame = ctk.CTkFrame(self, fg_color="transparent")
        cajas_frame.pack(fill="both", expand=True, padx=20, pady=(20, 8))

        self._caja_texto(
            cajas_frame, "Ticket", imp.renderizar_texto(self.datos_ticket),
            lado="left" if self.datos_comanda else None,
        )
        if self.datos_comanda:
            self._caja_texto(
                cajas_frame, "Comanda", imp.renderizar_texto_comanda(self.datos_comanda), lado="right",
            )

        self.label_estado = ctk.CTkLabel(self, text="", wraplength=700 if self.datos_comanda else 390, justify="left")
        self.label_estado.pack(fill="x", padx=20)

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=20, pady=(8, 20))
        self.btn_imprimir = ctk.CTkButton(
            botones, text="Imprimir", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, command=self._imprimir,
        )
        self.btn_imprimir.pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Cerrar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _caja_texto(self, master, titulo, texto, lado):
        contenedor = ctk.CTkFrame(master, fg_color="transparent")
        if lado:
            contenedor.pack(side=lado, fill="both", expand=True, padx=4)
        else:
            contenedor.pack(fill="both", expand=True)
        ctk.CTkLabel(
            contenedor, text=titulo, font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        caja = ctk.CTkTextbox(
            contenedor, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD,
            font=("Courier New", 12), wrap="none",
        )
        caja.pack(fill="both", expand=True)
        caja.insert("1.0", texto)
        caja.configure(state="disabled")

    def _imprimir(self):
        self.btn_imprimir.configure(text="Imprimiendo…", state="disabled")
        self.update_idletasks()

        if self._ticket_ok and self._comanda_ok:
            # Ambos ya se habían impreso con éxito: esto es un "imprimir de
            # nuevo" explícito (otra copia), no un reintento — se repiten
            # los dos a propósito.
            self._ticket_ok = False
            self._comanda_ok = not bool(self.datos_comanda)

        resultados = []

        if not self._ticket_ok:
            try:
                if self.venta_id is not None:
                    imp.imprimir_venta(self.venta_id)
                else:
                    imp.imprimir(self.datos_ticket)
                self._ticket_ok = True
                resultados.append("Ticket: impreso correctamente.")
            except imp.ImpresionError as e:
                resultados.append(f"Ticket: no se pudo imprimir ({e}).")
        else:
            resultados.append("Ticket: impreso correctamente.")

        if self.datos_comanda:
            if not self._comanda_ok:
                try:
                    if self.venta_id is not None:
                        imp.imprimir_comanda_de_venta(self.venta_id)
                    else:
                        imp.imprimir_comanda(self.datos_comanda)
                    self._comanda_ok = True
                    resultados.append("Comanda: impresa correctamente.")
                except imp.ImpresionError as e:
                    resultados.append(f"Comanda: no se pudo imprimir ({e}).")
            else:
                resultados.append("Comanda: impresa correctamente.")

        todo_ok = self._ticket_ok and self._comanda_ok
        if not todo_ok:
            resultados.append("La venta ya está registrada — puedes reintentar cuando quieras.")

        self.label_estado.configure(
            text="\n".join(resultados), text_color=theme.SUCCESS if todo_ok else theme.ERROR,
        )
        self.btn_imprimir.configure(
            text="Imprimir de nuevo" if todo_ok else "Reintentar impresión", state="normal",
        )
