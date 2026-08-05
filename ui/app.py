"""Ventana principal: login y enrutamiento entre pantallas según el rol."""
import customtkinter as ctk

from config import NEGOCIO_NOMBRE, VENTANA_ALTO, VENTANA_ANCHO
from ui import theme
from ui.admin.inventario_view import InventarioView
from ui.admin.reportes_view import ReportesView
from ui.admin.usuarios_view import UsuariosView
from ui.components.sidebar import Sidebar
from ui.login_view import LoginView
from ui.recetas.recetas_view import RecetasView
from ui.ventas.venta_view import VentaView

ADMIN_NAV_ITEMS = [
    {"key": "dashboard", "label": "Dashboard", "icon": "▦"},
    {"key": "inventario", "label": "Inventario", "icon": "◈"},
    {"key": "usuarios", "label": "Usuarios", "icon": "◔"},
    {"key": "reportes", "label": "Reportes", "icon": "▤"},
    {"key": "recetas", "label": "Recetas", "icon": "▥"},
]

PLACEHOLDER_FASES = {
    "dashboard": "Fase 6",
}


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{NEGOCIO_NOMBRE} · Punto de Venta")
        self.geometry(f"{VENTANA_ANCHO}x{VENTANA_ALTO}")
        self.minsize(1000, 650)
        self.configure(fg_color=theme.BG_PAGE)

        self.current_user = None
        self._content_frame = None

        self._show_login()

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _show_login(self):
        self.current_user = None
        self._clear()
        LoginView(self, on_login_success=self._handle_login_success).pack(fill="both", expand=True)

    def _handle_login_success(self, user):
        self.current_user = user
        if user.rol == "admin":
            self._show_admin_shell()
        else:
            self._show_vendedor_shell()

    def _show_admin_shell(self):
        self._clear()
        container = ctk.CTkFrame(self, fg_color=theme.BG_PAGE)
        container.pack(fill="both", expand=True)

        Sidebar(
            container,
            nav_items=ADMIN_NAV_ITEMS,
            current_user=self.current_user,
            on_navigate=self._navigate_admin,
            on_logout=self._show_login,
            on_ir_a_venta=self._show_vendedor_shell,
        ).pack(side="left", fill="y")

        self._content_frame = ctk.CTkFrame(container, fg_color=theme.BG_PAGE)
        self._content_frame.pack(side="left", fill="both", expand=True, padx=24, pady=24)

        self._navigate_admin("dashboard")

    def _navigate_admin(self, key):
        for widget in self._content_frame.winfo_children():
            widget.destroy()

        if key == "usuarios":
            UsuariosView(self._content_frame, current_user=self.current_user).pack(
                fill="both", expand=True
            )
        elif key == "inventario":
            InventarioView(self._content_frame, current_user=self.current_user).pack(
                fill="both", expand=True
            )
        elif key == "reportes":
            ReportesView(self._content_frame).pack(fill="both", expand=True)
        elif key == "recetas":
            RecetasView(self._content_frame, current_user=self.current_user, puede_editar=True).pack(
                fill="both", expand=True
            )
        else:
            self._placeholder(key)

    def _placeholder(self, key):
        fase = PLACEHOLDER_FASES.get(key, "una próxima fase")
        card = ctk.CTkFrame(self._content_frame, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="both", expand=True)

        contenido = ctk.CTkFrame(card, fg_color="transparent")
        contenido.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            contenido,
            text=f"{key.capitalize()}\n\nEste módulo se construye en la {fase}.",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        ).pack()

        if key == "dashboard":
            # Temporal: hasta que la Fase 6 tenga su propio dashboard, este
            # botón permite probar el formato del ticket con datos de
            # ejemplo sin necesidad de una venta real.
            ctk.CTkButton(
                contenido, text="🖨️  Probar impresión de ticket (datos de ejemplo)",
                corner_radius=theme.RADIUS_BUTTON, fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
                text_color=theme.TEXT_ON_ACCENT, command=self._probar_impresion,
            ).pack(pady=(16, 0))

    def _probar_impresion(self):
        from services import impresion_service as imp
        from ui.components.ticket_preview_view import TicketPreviewDialog

        TicketPreviewDialog(self, imp.datos_ticket_prueba())

    def _show_vendedor_shell(self, seccion="venta"):
        self._clear()
        container = ctk.CTkFrame(self, fg_color=theme.BG_PAGE)
        container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(container, fg_color=theme.BG_CARD, corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=f"Hola, {self.current_user.nombre}",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left", padx=24)

        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.pack(side="left", padx=16)

        activo = {"fg_color": theme.PINK, "text_color": theme.TEXT_ON_ACCENT, "hover_color": theme.PINK_HOVER}
        inactivo = {"fg_color": theme.BG_INPUT, "text_color": theme.TEXT_PRIMARY, "hover_color": theme.BG_HOVER}

        ctk.CTkButton(
            nav, text="🛍 Punto de venta", corner_radius=theme.RADIUS_BUTTON,
            command=lambda: self._show_vendedor_shell("venta"),
            **(activo if seccion == "venta" else inactivo),
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            nav, text="📖 Recetas", corner_radius=theme.RADIUS_BUTTON,
            command=lambda: self._show_vendedor_shell("recetas"),
            **(activo if seccion == "recetas" else inactivo),
        ).pack(side="left", padx=4)

        if self.current_user.rol == "admin":
            ctk.CTkButton(
                header, text="← Volver al dashboard", fg_color="transparent",
                text_color=theme.TEXT_SECONDARY, hover_color=theme.BG_HOVER,
                command=self._show_admin_shell,
            ).pack(side="left", padx=8)

        ctk.CTkButton(
            header, text="Cerrar sesión", fg_color=theme.BG_INPUT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            corner_radius=theme.RADIUS_BUTTON, command=self._show_login,
        ).pack(side="right", padx=24)

        body = ctk.CTkFrame(container, fg_color=theme.BG_PAGE)
        body.pack(fill="both", expand=True, padx=24, pady=24)

        if seccion == "recetas":
            # Solo lectura aquí siempre, sin importar el rol: la gestión
            # completa de recetas vive en el sidebar del administrador.
            RecetasView(body, current_user=self.current_user, puede_editar=False).pack(fill="both", expand=True)
        else:
            VentaView(body, current_user=self.current_user).pack(fill="both", expand=True)
