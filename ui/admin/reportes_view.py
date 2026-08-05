"""Panel de reportes y minería de datos para el administrador: ventas por
rango de fechas, productos más vendidos, ingresos por método de pago,
ventas por empleado y consumo de boba/perlas explosivas, con gráficas
embebidas (matplotlib)."""
import datetime

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from services import reporte_service as rep
from ui import theme

TIPOS_EXTRAS_BEBIDA = ["boba", "perla_explosiva"]


def _hoy():
    return datetime.date.today()


class ReportesView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.desde = _hoy() - datetime.timedelta(days=6)
        self.hasta = _hoy()
        self.body = None
        self._build_header()
        self._render_body()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header, text="Reportes", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")

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
        """Marca en azul fuerte el botón de rango rápido que corresponde al
        filtro actualmente aplicado (ninguno si el rango es manual)."""
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

    def _render_body(self):
        if self.body is not None:
            self.body.destroy()
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)

        desde_str = self.desde.isoformat()
        hasta_str = self.hasta.isoformat()

        resumen = rep.resumen_ventas(desde_str, hasta_str)
        if resumen["num_ventas"] == 0:
            self._estado_vacio(self.body)
            return

        self._kpis(self.body, resumen)

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

        self._lista_consumo_extras(self.body, rep.consumo_insumos(desde_str, hasta_str, tipos=TIPOS_EXTRAS_BEBIDA))

    def _estado_vacio(self, master):
        card = ctk.CTkFrame(master, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD, height=320)
        card.pack(fill="both", expand=True)
        card.pack_propagate(False)

        contenido = ctk.CTkFrame(card, fg_color="transparent")
        contenido.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(contenido, text="📭", font=(theme.FONT_FAMILY, 40)).pack(pady=(0, 12))
        ctk.CTkLabel(
            contenido, text="No hay ventas que mostrar en este rango de fechas",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), justify="center",
        ).pack()
        ctk.CTkLabel(
            contenido, text="Prueba con otro rango, o registra una venta desde el punto de venta.",
            text_color=theme.TEXT_SECONDARY, justify="center",
        ).pack(pady=(4, 0))

    def _kpis(self, master, resumen):
        fila = ctk.CTkFrame(master, fg_color="transparent")
        fila.pack(fill="x")
        for col in range(4):
            fila.grid_columnconfigure(col, weight=1)

        tarjetas = [
            ("🛍", "Ventas del período", str(resumen["num_ventas"])),
            ("$", "Ingresos totales", f"${resumen['ingresos_totales']:.2f}"),
            ("📈", "Ticket promedio", f"${resumen['ticket_promedio']:.2f}"),
            ("🏷", "Descuento aplicado", f"${resumen['descuento_total']:.2f}"),
        ]
        for i, (icono, titulo, valor) in enumerate(tarjetas):
            card = ctk.CTkFrame(fila, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            ctk.CTkLabel(
                card, text=icono, width=36, height=36, fg_color=theme.BLUE_SOFT, corner_radius=18,
                font=(theme.FONT_FAMILY, 16),
            ).pack(anchor="w", padx=16, pady=(16, 8))
            ctk.CTkLabel(card, text=titulo, text_color=theme.TEXT_SECONDARY, anchor="w").pack(anchor="w", padx=16)
            ctk.CTkLabel(
                card, text=valor, font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"), anchor="w",
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
