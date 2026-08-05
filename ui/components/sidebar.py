"""Sidebar de navegación reutilizable para las pantallas de administrador."""
import customtkinter as ctk

from ui import theme


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, nav_items, current_user, on_navigate, on_logout, on_ir_a_venta=None):
        super().__init__(master, fg_color=theme.BG_CARD, width=230, corner_radius=0)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self._nav_buttons = {}

        nav_container = ctk.CTkFrame(self, fg_color="transparent")
        nav_container.pack(fill="x", padx=12, pady=(24, 0))

        for item in nav_items:
            btn = ctk.CTkButton(
                nav_container,
                text=f"  {item['icon']}   {item['label']}",
                anchor="w",
                corner_radius=theme.RADIUS_BUTTON,
                fg_color="transparent",
                text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BG_HOVER,
                height=44,
                command=lambda k=item["key"]: self._handle_click(k),
            )
            btn.pack(fill="x", pady=4)
            self._nav_buttons[item["key"]] = btn

        if nav_items:
            self._set_active(nav_items[0]["key"])

        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", side="bottom", padx=12, pady=16)

        if on_ir_a_venta:
            ctk.CTkButton(
                bottom, text="🏪  Ir al punto de venta", anchor="w",
                fg_color="transparent", text_color=theme.TEXT_PRIMARY,
                hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON,
                height=40, command=on_ir_a_venta,
            ).pack(fill="x", pady=(0, 12))

        user_row = ctk.CTkFrame(bottom, fg_color="transparent")
        user_row.pack(fill="x")

        ctk.CTkLabel(
            user_row, text=current_user.nombre[0].upper(), width=36, height=36,
            fg_color=theme.PINK, text_color=theme.TEXT_ON_ACCENT, corner_radius=18,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(side="left")

        info = ctk.CTkFrame(user_row, fg_color="transparent")
        info.pack(side="left", padx=8, fill="x", expand=True)
        ctk.CTkLabel(
            info, text=current_user.nombre, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(fill="x")
        rol_label = "Administrador" if current_user.rol == "admin" else "Vendedor"
        ctk.CTkLabel(
            info, text=rol_label, anchor="w", text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(fill="x")

        ctk.CTkButton(
            user_row, text="⎋", width=32, height=32, corner_radius=16,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=on_logout,
        ).pack(side="right")

    def _handle_click(self, key):
        self._set_active(key)
        self.on_navigate(key)

    def _set_active(self, key):
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=theme.PINK, text_color=theme.TEXT_ON_ACCENT, hover_color=theme.PINK)
            else:
                btn.configure(fg_color="transparent", text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER)
