"""Pantalla de inicio de sesión."""
import customtkinter as ctk
from PIL import Image

from config import LOGO_PATH
from services import auth_service
from ui import theme

# El logo original es 3300x2550 (relación ~1.29:1) — se muestra afuera y
# arriba de la tarjeta de credenciales, a este tamaño.
LOGO_ANCHO = 560
LOGO_ALTO = 434


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=theme.BG_PAGE)
        self.on_login_success = on_login_success
        self._build()

    def _build(self):
        logo_imagen = Image.open(LOGO_PATH)
        self.logo = ctk.CTkImage(light_image=logo_imagen, dark_image=logo_imagen, size=(LOGO_ANCHO, LOGO_ALTO))
        ctk.CTkLabel(self, image=self.logo, text="").place(relx=0.5, rely=0.20, anchor="center")

        card = ctk.CTkFrame(
            self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD,
            width=420, height=400,
        )
        card.place(relx=0.5, rely=0.62, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=32, pady=32)

        ctk.CTkLabel(inner, text="Usuario", anchor="w").pack(fill="x")
        self.entry_usuario = ctk.CTkEntry(
            inner, placeholder_text="tu.usuario", corner_radius=theme.RADIUS_INPUT,
            fg_color=theme.BG_INPUT, border_width=0, height=44,
        )
        self.entry_usuario.pack(fill="x", pady=(4, 16))

        ctk.CTkLabel(inner, text="Contraseña", anchor="w").pack(fill="x")
        self.entry_password = ctk.CTkEntry(
            inner, placeholder_text="••••••••", show="•", corner_radius=theme.RADIUS_INPUT,
            fg_color=theme.BG_INPUT, border_width=0, height=44,
        )
        self.entry_password.pack(fill="x", pady=(4, 8))
        self.entry_password.bind("<Return>", lambda _e: self._submit())
        self.entry_usuario.bind("<Return>", lambda _e: self._submit())

        self.label_error = ctk.CTkLabel(
            inner, text="", text_color=theme.ERROR, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        )
        self.label_error.pack(fill="x", pady=(0, 8))

        self.btn_submit = ctk.CTkButton(
            inner, text="Iniciar sesión  →", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), height=48,
            command=self._submit,
        )
        self.btn_submit.pack(fill="x", pady=(8, 0))

        self.entry_usuario.focus_set()

    def _submit(self):
        usuario = self.entry_usuario.get()
        password = self.entry_password.get()
        try:
            user = auth_service.login(usuario, password)
        except auth_service.AuthError as e:
            self.label_error.configure(text=str(e))
            return
        self.label_error.configure(text="")
        self.entry_password.delete(0, "end")
        self.on_login_success(user)
