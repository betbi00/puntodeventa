"""Gestión de usuarios: alta, reseteo de contraseña y activar/desactivar."""
import customtkinter as ctk

from services import auth_service
from ui import theme


class UsuariosView(ctk.CTkFrame):
    def __init__(self, master, current_user):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self._build()
        self._refrescar()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header, text="Usuarios", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nuevo usuario", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
            command=self._abrir_form_nuevo,
        ).pack(side="right")

        self.lista_frame = ctk.CTkScrollableFrame(
            self, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD,
        )
        self.lista_frame.pack(fill="both", expand=True)

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()
        for usuario in auth_service.listar_usuarios():
            self._fila_usuario(usuario)

    def _fila_usuario(self, usuario):
        row = ctk.CTkFrame(self.lista_frame, fg_color="transparent")
        row.pack(fill="x", pady=8, padx=8)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            info, text=usuario.nombre, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(anchor="w")

        detalle = ctk.CTkFrame(info, fg_color="transparent")
        detalle.pack(anchor="w")

        rol_texto = "Administrador" if usuario.rol == "admin" else "Vendedor"
        ctk.CTkLabel(
            detalle, text=f"@{usuario.usuario} · {rol_texto} · ",
            text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(side="left")

        estado_texto = "Activo" if usuario.activo else "Inactivo"
        estado_color = theme.SUCCESS if usuario.activo else theme.TEXT_SECONDARY
        ctk.CTkLabel(
            detalle, text=estado_texto, text_color=estado_color,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold"),
        ).pack(side="left")

        acciones = ctk.CTkFrame(row, fg_color="transparent")
        acciones.pack(side="right")

        ctk.CTkButton(
            acciones, text="Resetear contraseña", width=150, height=32,
            corner_radius=theme.RADIUS_BUTTON, fg_color=theme.BLUE_SOFT,
            text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
            command=lambda u=usuario: self._abrir_form_reset(u),
        ).pack(side="left", padx=4)

        es_uno_mismo = usuario.id == self.current_user.id
        ctk.CTkButton(
            acciones,
            text=("Desactivar" if usuario.activo else "Activar"),
            width=100, height=32, corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=lambda u=usuario: self._toggle_activo(u),
            state="disabled" if es_uno_mismo else "normal",
        ).pack(side="left", padx=4)

    def _toggle_activo(self, usuario):
        auth_service.set_activo(usuario.id, not usuario.activo)
        self._refrescar()

    def _abrir_form_nuevo(self):
        FormularioUsuario(self, on_guardado=self._refrescar)

    def _abrir_form_reset(self, usuario):
        FormularioResetPassword(self, usuario, on_guardado=self._refrescar)


class FormularioUsuario(ctk.CTkToplevel):
    def __init__(self, master, on_guardado):
        super().__init__(master)
        self.title("Nuevo usuario")
        self.geometry("380x440")
        self.configure(fg_color=theme.BG_PAGE)
        self.on_guardado = on_guardado
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Nombre completo", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_nombre = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(self, text="Usuario", anchor="w").pack(fill="x", padx=24)
        self.entry_usuario = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_usuario.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(self, text="Contraseña", anchor="w").pack(fill="x", padx=24)
        self.entry_password = ctk.CTkEntry(self, show="•", fg_color=theme.BG_INPUT, border_width=0)
        self.entry_password.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(self, text="Rol", anchor="w").pack(fill="x", padx=24)
        self.option_rol = ctk.CTkOptionMenu(self, values=["vendedor", "admin"], fg_color=theme.BG_INPUT)
        self.option_rol.pack(fill="x", padx=24, pady=(0, 12))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Crear usuario", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24))

    def _guardar(self):
        try:
            auth_service.crear_usuario(
                self.entry_nombre.get(),
                self.entry_usuario.get(),
                self.entry_password.get(),
                self.option_rol.get(),
            )
        except auth_service.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()


class FormularioResetPassword(ctk.CTkToplevel):
    def __init__(self, master, usuario, on_guardado):
        super().__init__(master)
        self.title(f"Resetear contraseña · {usuario.usuario}")
        self.geometry("360x220")
        self.configure(fg_color=theme.BG_PAGE)
        self.usuario = usuario
        self.on_guardado = on_guardado
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text=f"Nueva contraseña para {self.usuario.nombre}", anchor="w",
        ).pack(fill="x", padx=24, pady=(24, 4))
        self.entry_password = ctk.CTkEntry(self, show="•", fg_color=theme.BG_INPUT, border_width=0)
        self.entry_password.pack(fill="x", padx=24, pady=(0, 12))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR)
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24))

    def _guardar(self):
        try:
            auth_service.resetear_password(self.usuario.id, self.entry_password.get())
        except auth_service.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()
