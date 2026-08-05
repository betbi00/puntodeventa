"""Vista de recetas: cada tarjeta muestra la miniatura del video de
preparación y un botón para verlo en el navegador. El administrador puede
crear/editar/eliminar; el vendedor solo ve y abre los videos (solo
lectura)."""
import webbrowser
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from services import receta_service as recetas
from ui import theme

COLUMNAS = 3
TAMANO_MINIATURA = (220, 124)


class RecetasView(ctk.CTkFrame):
    def __init__(self, master, current_user, puede_editar=None):
        super().__init__(master, fg_color="transparent")
        self.current_user = current_user
        self.puede_editar = puede_editar if puede_editar is not None else (current_user.rol == "admin")
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            header, text="Recetas", font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(side="left")
        if self.puede_editar:
            ctk.CTkButton(
                header, text="+ Nueva receta", corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.PINK, hover_color=theme.PINK_HOVER, text_color=theme.TEXT_ON_ACCENT,
                command=self._abrir_form_nuevo,
            ).pack(side="right")

        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        for col in range(COLUMNAS):
            self.grid_frame.grid_columnconfigure(col, weight=1)

        self._refrescar()

    def _refrescar(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        lista = recetas.listar_recetas()
        if not lista:
            texto = (
                "Todavía no hay recetas registradas. Usa \"+ Nueva receta\" para agregar la primera."
                if self.puede_editar else
                "Todavía no hay recetas disponibles."
            )
            ctk.CTkLabel(self.grid_frame, text=texto, text_color=theme.TEXT_SECONDARY).grid(
                row=0, column=0, columnspan=COLUMNAS, pady=40
            )
            return

        for index, receta in enumerate(lista):
            fila, columna = divmod(index, COLUMNAS)
            self._tarjeta_receta(receta, fila, columna)

    def _tarjeta_receta(self, receta, fila, columna):
        card = ctk.CTkFrame(self.grid_frame, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.grid(row=fila, column=columna, padx=8, pady=8, sticky="nsew")

        self._miniatura(card, receta)

        ctk.CTkLabel(
            card, text=receta.nombre_producto, font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
            wraplength=200,
        ).pack(padx=8, pady=(0, 8))

        ctk.CTkButton(
            card, text="▶ Ver receta", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BLUE_SOFT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
            command=lambda url=receta.video_url: webbrowser.open(url),
        ).pack(fill="x", padx=8, pady=(0, 8))

        if self.puede_editar:
            acciones = ctk.CTkFrame(card, fg_color="transparent")
            acciones.pack(fill="x", padx=8, pady=(0, 8))
            ctk.CTkButton(
                acciones, text="Editar", height=28, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
                command=lambda r=receta: self._abrir_form_editar(r),
            ).pack(side="left", expand=True, fill="x", padx=(0, 4))
            ctk.CTkButton(
                acciones, text="Eliminar", height=28, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, text_color=theme.ERROR, hover_color=theme.BG_HOVER,
                command=lambda r=receta: self._confirmar_eliminar(r),
            ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _miniatura(self, master, receta):
        if receta.miniatura_path and Path(receta.miniatura_path).exists():
            try:
                imagen = Image.open(receta.miniatura_path)
                ctk_imagen = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=TAMANO_MINIATURA)
                ctk.CTkLabel(master, image=ctk_imagen, text="").pack(padx=8, pady=(8, 4))
                return
            except Exception:
                pass
        ctk.CTkLabel(
            master, text="🎬", fg_color=theme.BG_INPUT, corner_radius=theme.RADIUS_INPUT,
            width=TAMANO_MINIATURA[0], height=TAMANO_MINIATURA[1], font=(theme.FONT_FAMILY, 32),
        ).pack(padx=8, pady=(8, 4))

    def _abrir_form_nuevo(self):
        FormularioReceta(self, receta=None, current_user=self.current_user, on_guardado=self._refrescar)

    def _abrir_form_editar(self, receta):
        FormularioReceta(self, receta=receta, current_user=self.current_user, on_guardado=self._refrescar)

    def _confirmar_eliminar(self, receta):
        ConfirmarEliminarReceta(self, receta, on_confirmado=self._refrescar)


class FormularioReceta(ctk.CTkToplevel):
    def __init__(self, master, receta, current_user, on_guardado):
        super().__init__(master)
        self.receta = receta
        self.current_user = current_user
        self.on_guardado = on_guardado
        self.ruta_miniatura_manual = None

        self.title("Editar receta" if receta else "Nueva receta")
        self.geometry("420x500")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Nombre del producto", anchor="w").pack(fill="x", padx=24, pady=(24, 4))
        self.entry_nombre = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", padx=24, pady=(0, 12))
        if self.receta:
            self.entry_nombre.insert(0, self.receta.nombre_producto)

        ctk.CTkLabel(self, text="Link del video de YouTube (privado/no listado)", anchor="w").pack(
            fill="x", padx=24
        )
        self.entry_url = ctk.CTkEntry(self, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_url.pack(fill="x", padx=24, pady=(0, 12))
        if self.receta:
            self.entry_url.insert(0, self.receta.video_url)

        ctk.CTkLabel(
            self, text="La miniatura se intenta obtener automáticamente del video. "
                       "Si prefieres subir tú una imagen:",
            text_color=theme.TEXT_SECONDARY, wraplength=370, justify="left",
        ).pack(fill="x", padx=24, pady=(4, 4))
        self.label_miniatura = ctk.CTkLabel(
            self, text="Ninguna imagen seleccionada", text_color=theme.TEXT_SECONDARY, anchor="w",
        )
        self.label_miniatura.pack(fill="x", padx=24)
        ctk.CTkButton(
            self, text="Elegir imagen…", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=self._elegir_imagen,
        ).pack(fill="x", padx=24, pady=(4, 12))

        self.label_error = ctk.CTkLabel(self, text="", text_color=theme.ERROR, wraplength=370, justify="left")
        self.label_error.pack(fill="x", padx=24)

        ctk.CTkButton(
            self, text="Guardar", fg_color=theme.PINK, hover_color=theme.PINK_HOVER,
            text_color=theme.TEXT_ON_ACCENT, corner_radius=theme.RADIUS_BUTTON, height=48,
            command=self._guardar,
        ).pack(fill="x", padx=24, pady=(12, 24), side="bottom")

    def _elegir_imagen(self):
        ruta = filedialog.askopenfilename(
            parent=self, title="Elegir miniatura",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg")],
        )
        if ruta:
            self.ruta_miniatura_manual = ruta
            self.label_miniatura.configure(text=Path(ruta).name)

    def _guardar(self):
        nombre = self.entry_nombre.get()
        url = self.entry_url.get()
        try:
            if self.receta:
                recetas.actualizar_receta(
                    self.receta.id, nombre, url, miniatura_manual=self.ruta_miniatura_manual,
                )
            else:
                recetas.crear_receta(
                    nombre, url, creado_por=self.current_user.id, miniatura_manual=self.ruta_miniatura_manual,
                )
        except recetas.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()


class ConfirmarEliminarReceta(ctk.CTkToplevel):
    def __init__(self, master, receta, on_confirmado):
        super().__init__(master)
        self.receta = receta
        self.on_confirmado = on_confirmado

        self.title("Eliminar receta")
        self.geometry("360x200")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f'¿Eliminar la receta de "{receta.nombre_producto}"? Esta acción no se puede deshacer.',
            wraplength=310, justify="left",
        ).pack(fill="x", padx=24, pady=(24, 16))

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            botones, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Sí, eliminar", fg_color=theme.ERROR, hover_color=theme.ERROR,
            text_color="#FFFFFF", corner_radius=theme.RADIUS_BUTTON, command=self._eliminar,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _eliminar(self):
        recetas.eliminar_receta(self.receta.id)
        self.destroy()
        self.on_confirmado()
