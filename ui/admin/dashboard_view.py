"""Dashboard del administrador: todo en un solo lugar — ventas por rango
de fechas, ingresos, gastos y utilidad neta, gráficas, productos más
vendidos, ventas por empleado, consumo de boba/perlas, exportar a PDF,
y el panel para registrar gastos del negocio (renta, agua, luz, etc.).

Antes esto estaba dividido entre "Dashboard" (fijo, hoy/semana) y
"Reportes" (con filtro de fechas) — se fusionaron porque duplicaban casi
todo. Ahora hay una sola pantalla y un solo filtro de fechas que controla
todo lo que se ve."""
import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from services import pdf_service
from services import reporte_service as rep
from ui import theme
from ui.admin.gastos_view import GastosPanel
from ui.admin.promociones_view import PromocionesPanel

TIPOS_EXTRAS_BEBIDA = ["boba", "perla_explosiva"]
COLUMNAS_KPI = 3


def _hoy():
    return datetime.date.today()


class DashboardView(ctk.CTkFrame):
    def __init__(self, master, current_user, on_probar_impresion=None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self.on_probar_impresion = on_probar_impresion
        self.desde = _hoy() - datetime.timedelta(days=6)
        self.hasta = _hoy()
        self._build_header()
        self._build_footer()

        # El área de contenido se crea UNA sola vez. CTkScrollableFrame no
        # se limpia bien si se destruye y se vuelve a crear repetidamente
        # (deja barras de scroll "fantasma" apiladas) — en cada refresco
        # solo se vacían sus hijos, nunca el frame en sí.
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        self._render_body()

    def _build_footer(self):
        """Barra fija abajo, siempre visible sin necesidad de bajar con el
        scroll: probar impresión a la izquierda, exportar a PDF a la
        derecha (en esquinas opuestas a propósito)."""
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=(12, 0))

        if self.on_probar_impresion:
            lado_izquierdo = ctk.CTkFrame(footer, fg_color="transparent")
            lado_izquierdo.pack(side="left")
            ctk.CTkButton(
                lado_izquierdo, text="Probar impresión de ticket", corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, hover_color=theme.BG_HOVER, text_color=theme.TEXT_PRIMARY,
                command=self.on_probar_impresion,
            ).pack(side="left")

        ctk.CTkButton(
            footer, text="Exportar a PDF", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BLUE, hover_color=theme.BLUE_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._exportar_pdf,
        ).pack(side="right")

    def _build_header(self):
        fila_titulo = ctk.CTkFrame(self, fg_color="transparent")
        fila_titulo.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            fila_titulo, text="Dashboard", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        filtros = ctk.CTkFrame(header, fg_color="transparent")
        filtros.pack(side="right")

        self.botones_rango = {}
        for etiqueta, dias in [("Hoy", 0), ("7 días", 6), ("30 días", 29)]:
            boton = ctk.CTkButton(
                filtros, text=etiqueta, width=70, height=32, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BLUE_SOFT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
                command=lambda d=dias: self._set_rango_rapido(d),
            )
            boton.pack(side="left", padx=2)
            self.botones_rango[dias] = boton

        ctk.CTkLabel(filtros, text="Desde").pack(side="left", padx=(12, 4))
        self.entry_desde = ctk.CTkEntry(filtros, width=100, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_desde.insert(0, self.desde.isoformat())
        self.entry_desde.pack(side="left", padx=4)

        ctk.CTkLabel(filtros, text="Hasta").pack(side="left", padx=(8, 4))
        self.entry_hasta = ctk.CTkEntry(filtros, width=100, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_hasta.insert(0, self.hasta.isoformat())
        self.entry_hasta.pack(side="left", padx=4)

        ctk.CTkButton(
            filtros, text="Aplicar", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._aplicar_filtro,
        ).pack(side="left", padx=(8, 4))

        ctk.CTkButton(
            filtros, text="✕", width=32, height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_SECONDARY, hover_color=theme.BG_HOVER,
            command=self._restablecer_filtro,
        ).pack(side="left", padx=(4, 0))

        self._resaltar_boton_activo(6)

    def _resaltar_boton_activo(self, dias_activos):
        for dias, boton in self.botones_rango.items():
            if dias == dias_activos:
                boton.configure(fg_color=theme.BLUE, text_color=theme.TEXT_ON_ACCENT, hover_color=theme.BLUE)
            else:
                boton.configure(fg_color=theme.BLUE_SOFT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE)

    def _restablecer_filtro(self):
        self._set_rango_rapido(6)

    def _set_rango_rapido(self, dias_atras):
        self.hasta = _hoy()
        self.desde = _hoy() - datetime.timedelta(days=dias_atras)
        self.entry_desde.delete(0, "end")
        self.entry_desde.insert(0, self.desde.isoformat())
        self.entry_hasta.delete(0, "end")
        self.entry_hasta.insert(0, self.hasta.isoformat())
        self._resaltar_boton_activo(dias_atras)
        self._render_body()

    def _aplicar_filtro(self):
        try:
            nuevo_desde = datetime.date.fromisoformat(self.entry_desde.get().strip())
            nuevo_hasta = datetime.date.fromisoformat(self.entry_hasta.get().strip())
        except ValueError:
            return
        self.desde, self.hasta = nuevo_desde, nuevo_hasta
        self._resaltar_boton_activo(None)
        self._render_body()

    def _exportar_pdf(self):
        nombre_sugerido = f"reporte_{self.desde.isoformat()}_a_{self.hasta.isoformat()}.pdf"
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar reporte como", defaultextension=".pdf",
            initialfile=nombre_sugerido, filetypes=[("PDF", "*.pdf")],
        )
        if not ruta:
            return
        try:
            pdf_service.exportar_pdf(self.desde.isoformat(), self.hasta.isoformat(), ruta)
        except Exception as e:
            messagebox.showerror("Error al exportar", f"No se pudo generar el archivo:\n{e}", parent=self)
            return
        messagebox.showinfo("Reporte exportado", f"Se guardó correctamente en:\n{ruta}", parent=self)

    def _render_body(self):
        for widget in self.body.winfo_children():
            widget.destroy()

        desde_str = self.desde.isoformat()
        hasta_str = self.hasta.isoformat()

        resumen = rep.resumen_ventas(desde_str, hasta_str)
        gastos_total = rep.resumen_gastos(desde_str, hasta_str)
        self._kpis(self.body, resumen, gastos_total)

        if resumen["num_ventas"] == 0:
            self._estado_vacio(self.body)
        else:
            graficas = ctk.CTkFrame(self.body, fg_color="transparent")
            graficas.pack(fill="x", pady=(16, 0))
            graficas.grid_columnconfigure(0, weight=2)
            graficas.grid_columnconfigure(1, weight=1)

            self._grafica_ventas_por_dia(graficas, rep.ventas_por_dia(desde_str, hasta_str))
            self._grafica_metodo_pago(graficas, resumen)

            listas = ctk.CTkFrame(self.body, fg_color="transparent")
            listas.pack(fill="x", pady=(16, 0))
            listas.grid_columnconfigure(0, weight=1)
            listas.grid_columnconfigure(1, weight=1)

            self._lista_productos(listas, rep.productos_mas_vendidos(desde_str, hasta_str), columna=0)
            self._lista_empleados(listas, rep.ventas_por_empleado(desde_str, hasta_str), columna=1)

            self._lista_consumo_extras(
                self.body, rep.consumo_insumos(desde_str, hasta_str, tipos=TIPOS_EXTRAS_BEBIDA)
            )

            self._lista_promociones(self.body, rep.promociones_uso(desde_str, hasta_str))

        PromocionesPanel(self.body).pack(fill="x", pady=(16, 0))
        GastosPanel(self.body, current_user=self.current_user).pack(fill="x", pady=(16, 0))

    def _estado_vacio(self, master):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD, height=220)
        card.pack(fill="both", pady=(16, 0))
        card.pack_propagate(False)

        contenido = ctk.CTkFrame(card, fg_color="transparent")
        contenido.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            contenido, text="No hay ventas que mostrar en este rango de fechas",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), justify="center",
        ).pack()
        ctk.CTkLabel(
            contenido, text="Prueba con otro rango, o registra una venta desde el punto de venta.",
            text_color=theme.TEXT_SECONDARY, justify="center",
        ).pack(pady=(4, 0))

    def _kpis(self, master, resumen, gastos_total):
        utilidad_neta = resumen["ingresos_totales"] - gastos_total

        fila = ctk.CTkFrame(master, fg_color="transparent")
        fila.pack(fill="x")
        for col in range(COLUMNAS_KPI):
            fila.grid_columnconfigure(col, weight=1)

        tarjetas = [
            ("🛍", "Ventas del período", str(resumen["num_ventas"]), None),
            ("$", "Ingresos totales", f"${resumen['ingresos_totales']:.2f}", None),
            ("📈", "Ticket promedio", f"${resumen['ticket_promedio']:.2f}", None),
            ("🏷", "Descuento aplicado", f"${resumen['descuento_total']:.2f}", None),
            ("💸", "Gastos totales", f"${gastos_total:.2f}", None),
            ("⚖️", "Utilidad neta", f"${utilidad_neta:.2f}",
             theme.SUCCESS if utilidad_neta >= 0 else theme.ERROR),
        ]
        for i, (icono, titulo, valor, color_valor) in enumerate(tarjetas):
            fila_grid, columna_grid = divmod(i, COLUMNAS_KPI)
            card = ctk.CTkFrame(fila, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
            card.grid(row=fila_grid, column=columna_grid, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(
                card, text=icono, width=36, height=36, fg_color=theme.BLUE_SOFT, corner_radius=18,
                font=(theme.FONT_FAMILY, 16),
            ).pack(anchor="w", padx=16, pady=(16, 8))
            ctk.CTkLabel(card, text=titulo, text_color=theme.TEXT_SECONDARY, anchor="w").pack(anchor="w", padx=16)
            ctk.CTkLabel(
                card, text=valor, font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"), anchor="w",
                text_color=color_valor or theme.TEXT_PRIMARY,
            ).pack(anchor="w", padx=16, pady=(0, 16))

    def _grafica_ventas_por_dia(self, master, datos):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        ctk.CTkLabel(
            card, text="Ventas por día", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), anchor="w",
        ).pack(anchor="w", padx=16, pady=(16, 4))

        fig = Figure(figsize=(5, 3), dpi=100, facecolor=theme.BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme.BG_CARD)

        if datos:
            dias = [d["dia"][5:] for d in datos]
            ingresos = [d["ingresos"] for d in datos]
            ax.bar(dias, ingresos, color=theme.PINK)
        else:
            ax.text(0.5, 0.5, "Sin ventas en este rango", ha="center", va="center", color=theme.TEXT_SECONDARY)
            ax.set_xticks([])
            ax.set_yticks([])

        ax.tick_params(colors=theme.TEXT_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(theme.BORDER)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _grafica_metodo_pago(self, master, resumen):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        ctk.CTkLabel(
            card, text="Ingresos por método de pago", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            anchor="w",
        ).pack(anchor="w", padx=16, pady=(16, 4))

        fig = Figure(figsize=(3, 3), dpi=100, facecolor=theme.BG_CARD)
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme.BG_CARD)

        valores = [resumen["ingresos_efectivo"], resumen["ingresos_tarjeta"]]
        if sum(valores) > 0:
            ax.pie(
                valores, labels=["Efectivo", "Tarjeta"], colors=[theme.PINK, theme.BLUE],
                autopct="%1.0f%%", textprops={"color": theme.TEXT_PRIMARY, "fontsize": 8},
            )
        else:
            ax.text(0.5, 0.5, "Sin ventas", ha="center", va="center", color=theme.TEXT_SECONDARY)
            ax.axis("off")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _lista_productos(self, master, datos, columna):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.grid(row=0, column=columna, padx=(0, 8) if columna == 0 else (8, 0), sticky="nsew")
        ctk.CTkLabel(
            card, text="Productos más vendidos", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), anchor="w",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        if not datos:
            ctk.CTkLabel(card, text="Sin ventas en este rango", text_color=theme.TEXT_SECONDARY).pack(
                padx=16, pady=(0, 16)
            )
            return

        maximo = max(d["cantidad"] for d in datos)
        for i, item in enumerate(datos, start=1):
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=16, pady=4)

            encabezado = ctk.CTkFrame(fila, fg_color="transparent")
            encabezado.pack(fill="x")
            ctk.CTkLabel(encabezado, text=f"{i}. {item['nombre']}", anchor="w").pack(side="left")
            ctk.CTkLabel(encabezado, text=str(item["cantidad"]), text_color=theme.TEXT_SECONDARY).pack(side="right")

            barra_fondo = ctk.CTkFrame(fila, fg_color=theme.BG_INPUT, height=8, corner_radius=4)
            barra_fondo.pack(fill="x", pady=(4, 0))
            proporcion = item["cantidad"] / maximo if maximo else 0
            barra = ctk.CTkFrame(barra_fondo, fg_color=theme.PINK, height=8, corner_radius=4)
            barra.place(relx=0, rely=0, relwidth=max(0.03, proporcion), relheight=1)

        ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def _lista_empleados(self, master, datos, columna):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.grid(row=0, column=columna, padx=(0, 8) if columna == 0 else (8, 0), sticky="nsew")
        ctk.CTkLabel(
            card, text="Ventas por empleado", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), anchor="w",
        ).pack(anchor="w", padx=16, pady=(16, 8))

        if not datos:
            ctk.CTkLabel(card, text="Sin ventas en este rango", text_color=theme.TEXT_SECONDARY).pack(
                padx=16, pady=(0, 16)
            )
            return

        for item in datos:
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(fila, text=item["nombre"], anchor="w").pack(side="left")
            ctk.CTkLabel(
                fila, text=f"{item['num_ventas']} ventas · ${item['ingresos']:.2f}",
                text_color=theme.TEXT_SECONDARY,
            ).pack(side="right")

        ctk.CTkFrame(card, fg_color="transparent", height=8).pack()

    def _lista_consumo_extras(self, master, datos):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(
            card, text="Consumo de boba y perlas explosivas", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(
            card, text="Para control de inventario de estos insumos.", anchor="w",
            text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        if not datos:
            ctk.CTkLabel(card, text="Sin consumo en este rango", text_color=theme.TEXT_SECONDARY).pack(
                padx=16, pady=(0, 16)
            )
            return

        fila = ctk.CTkFrame(card, fg_color="transparent")
        fila.pack(fill="x", padx=16, pady=(0, 16))
        for item in datos:
            chip = ctk.CTkFrame(fila, fg_color=theme.BLUE_SOFT, corner_radius=theme.RADIUS_BUTTON)
            chip.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                chip, text=f"{item['nombre']}: {item['cantidad']:g}", text_color=theme.TEXT_PRIMARY,
            ).pack(padx=12, pady=8)

    def _lista_promociones(self, master, datos):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="x", pady=(16, 0))
        ctk.CTkLabel(
            card, text="Uso de promociones", anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        if not datos:
            ctk.CTkLabel(card, text="Ninguna promoción se usó en este rango", text_color=theme.TEXT_SECONDARY).pack(
                padx=16, pady=(0, 16)
            )
            return

        for item in datos:
            fila = ctk.CTkFrame(card, fg_color="transparent")
            fila.pack(fill="x", padx=16, pady=6)
            ctk.CTkLabel(fila, text=item["nombre"], anchor="w").pack(side="left")
            ctk.CTkLabel(
                fila, text=f"{item['num_usos']} usos · ${item['descuento_total']:.2f} en descuentos",
                text_color=theme.TEXT_SECONDARY,
            ).pack(side="right")

        ctk.CTkFrame(card, fg_color="transparent", height=8).pack()
