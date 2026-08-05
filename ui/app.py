"""Ventana principal: login y enrutamiento entre pantallas según el rol."""
import customtkinter as ctk

from config import NEGOCIO_NOMBRE, VENTANA_ALTO, VENTANA_ANCHO
from ui import theme
from ui.admin.usuarios_view import UsuariosView
from ui.components.sidebar import Sidebar
from ui.login_view import LoginView

ADMIN_NAV_ITEMS = [
    {"key": "dashboard", "label": "Dashboard", "icon": "▦"},
    {"key": "inventario", "label": "Inventario", "icon": "◈"},
    {"key": "usuarios", "label": "Usuarios", "icon": "◔"},
    {"key": "reportes", "label": "Reportes", "icon": "▤"},
    {"key": "recetas", "label": "Recetas", "icon": "▥"},
]

PLACEHOLDER_FASES = {
    "dashboard": "Fase 6",
    "inventario": "Fase 2",
    "reportes": "Fase 6",
    "recetas": "Fase 7",
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
        else:
            self._placeholder(key)

    def _placeholder(self, key):
        fase = PLACEHOLDER_FASES.get(key, "una próxima fase")
        card = ctk.CTkFrame(self._content_frame, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            card,
            text=f"{key.capitalize()}\n\nEste módulo se construye en la {fase}.",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE),
            text_color=theme.TEXT_SECONDARY,
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _show_vendedor_shell(self):
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

        card = ctk.CTkFrame(body, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            card, text="Punto de venta\n\nEste módulo se construye en la Fase 3.",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE), text_color=theme.TEXT_SECONDARY,
            justify="center",
        ).place(relx=0.5, rely=0.5, anchor="center")
