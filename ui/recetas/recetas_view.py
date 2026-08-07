"""Vista de recetas: cada fila muestra la miniatura del video junto con
los ingredientes y los pasos rápidos en texto, para consultarlos de un
vistazo sin tener que abrir el video. El administrador puede
crear/editar/Quitar; el vendedor solo ve y abre los videos (solo
lectura)."""
import webbrowser
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from services import receta_service as recetas
from ui import theme

TAMANO_MINIATURA = (180, 100)
ANCHO_COLUMNA_IZQUIERDA = 210


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

        self.lista_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.lista_frame.pack(fill="both", expand=True)

        self._refrescar()

    def _refrescar(self):
        for widget in self.lista_frame.winfo_children():
            widget.destroy()

        lista = recetas.listar_recetas()
        if not lista:
            texto = (
                "Todavía no hay recetas registradas. Usa \"+ Nueva receta\" para agregar la primera."
                if self.puede_editar else
                "Todavía no hay recetas disponibles."
            )
            ctk.CTkLabel(self.lista_frame, text=texto, text_color=theme.TEXT_SECONDARY).pack(pady=40)
            return

        for receta in lista:
            self._fila_receta(receta)

    def _fila_receta(self, receta):
        card = ctk.CTkFrame(self.lista_frame, fg_color=theme.BG_CARD, corner_radius=theme.RADIUS_CARD)
        card.pack(fill="x", pady=8, padx=4)

        contenido = ctk.CTkFrame(card, fg_color="transparent")
        contenido.pack(fill="x", padx=16, pady=16)

        izquierda = ctk.CTkFrame(contenido, fg_color="transparent", width=ANCHO_COLUMNA_IZQUIERDA)
        izquierda.pack(side="left", padx=(0, 16))
        izquierda.pack_propagate(False)

        self._miniatura(izquierda, receta)
        ctk.CTkLabel(
            izquierda, text=receta.nombre_producto, anchor="w", justify="left",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"), wraplength=ANCHO_COLUMNA_IZQUIERDA - 10,
        ).pack(fill="x", pady=(8, 8))

        ctk.CTkButton(
            izquierda, text="Ver receta", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BLUE_SOFT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
            command=lambda url=receta.video_url: webbrowser.open(url),
        ).pack(fill="x")

        if self.puede_editar:
            acciones = ctk.CTkFrame(izquierda, fg_color="transparent")
            acciones.pack(fill="x", pady=(8, 0))
            ctk.CTkButton(
                acciones, text="Editar", height=28, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
                command=lambda r=receta: self._abrir_form_editar(r),
            ).pack(side="left", expand=True, fill="x", padx=(0, 3))
            ctk.CTkButton(
                acciones, text="Quitar", height=28, corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BG_INPUT, text_color=theme.ERROR, hover_color=theme.BG_HOVER,
                command=lambda r=receta: self._confirmar_Quitar(r),
            ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        derecha = ctk.CTkFrame(contenido, fg_color="transparent")
        derecha.pack(side="left", fill="both", expand=True)
        derecha.grid_columnconfigure(0, weight=1)
        derecha.grid_columnconfigure(1, weight=1)

        self._bloque_texto(derecha, "Ingredientes", receta.lista_ingredientes, columna=0)
        self._bloque_texto(derecha, "Pasos rápidos", receta.lista_pasos, columna=1, numerado=True)

    def _bloque_texto(self, master, titulo, items, columna, numerado=False):
        bloque = ctk.CTkFrame(master, fg_color=theme.BG_PAGE, corner_radius=theme.RADIUS_INPUT)
        bloque.grid(row=0, column=columna, sticky="nsew", padx=(0, 8) if columna == 0 else (8, 0))

        ctk.CTkLabel(
            bloque, text=titulo, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL, "bold"),
        ).pack(fill="x", padx=12, pady=(10, 4))

        if not items:
            ctk.CTkLabel(
                bloque, text="No especificado", anchor="w", text_color=theme.TEXT_SECONDARY,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            ).pack(fill="x", padx=12, pady=(0, 10))
            return

        for i, item in enumerate(items, start=1):
            prefijo = f"{i}. " if numerado else "•  "
            ctk.CTkLabel(
                bloque, text=prefijo + item, anchor="w", justify="left", wraplength=260,
                font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
            ).pack(fill="x", padx=12, pady=2)

        ctk.CTkFrame(bloque, fg_color="transparent", height=8).pack()

    def _miniatura(self, master, receta):
        if receta.miniatura_path and Path(receta.miniatura_path).exists():
            try:
                imagen = Image.open(receta.miniatura_path)
                ctk_imagen = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=TAMANO_MINIATURA)
                ctk.CTkLabel(master, image=ctk_imagen, text="").pack()
                return
            except Exception:
                pass
        ctk.CTkLabel(
            master, text="🎬", fg_color=theme.BG_INPUT, corner_radius=theme.RADIUS_INPUT,
            width=TAMANO_MINIATURA[0], height=TAMANO_MINIATURA[1], font=(theme.FONT_FAMILY, 32),
        ).pack()

    def _abrir_form_nuevo(self):
        FormularioReceta(self, receta=None, current_user=self.current_user, on_guardado=self._refrescar)

    def _abrir_form_editar(self, receta):
        FormularioReceta(self, receta=receta, current_user=self.current_user, on_guardado=self._refrescar)

    def _confirmar_Quitar(self, receta):
        ConfirmarQuitarReceta(self, receta, on_confirmado=self._refrescar)


class FormularioReceta(ctk.CTkToplevel):
    def __init__(self, master, receta, current_user, on_guardado):
        super().__init__(master)
        self.receta = receta
        self.current_user = current_user
        self.on_guardado = on_guardado
        self.ruta_miniatura_manual = None

        self.title("Editar receta" if receta else "Nueva receta")
        self.geometry("460x760")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        contenido = ctk.CTkScrollableFrame(self, fg_color="transparent")
        contenido.pack(fill="both", expand=True, padx=24, pady=(24, 0))

        ctk.CTkLabel(contenido, text="Nombre del producto", anchor="w").pack(fill="x", pady=(0, 4))
        self.entry_nombre = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_nombre.pack(fill="x", pady=(0, 12))
        if self.receta:
            self.entry_nombre.insert(0, self.receta.nombre_producto)

        ctk.CTkLabel(contenido, text="Link del video de YouTube (privado/no listado)", anchor="w").pack(fill="x")
        self.entry_url = ctk.CTkEntry(contenido, fg_color=theme.BG_INPUT, border_width=0)
        self.entry_url.pack(fill="x", pady=(0, 12))
        if self.receta:
            self.entry_url.insert(0, self.receta.video_url)

        ctk.CTkLabel(
            contenido, text="La miniatura se intenta obtener automáticamente del video. "
                            "Si prefieres subir tú una imagen:",
            text_color=theme.TEXT_SECONDARY, wraplength=380, justify="left",
        ).pack(fill="x", pady=(4, 4))
        self.label_miniatura = ctk.CTkLabel(
            contenido, text="Ninguna imagen seleccionada", text_color=theme.TEXT_SECONDARY, anchor="w",
        )
        self.label_miniatura.pack(fill="x")
        ctk.CTkButton(
            contenido, text="Elegir imagen…", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=self._elegir_imagen,
        ).pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(
            contenido, text="Ingredientes (uno por línea)", anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            contenido, text="Para consulta rápida al cobrar, sin tener que abrir el video.",
            text_color=theme.TEXT_SECONDARY, font=(theme.FONT_FAMILY, theme.FONT_SIZE_SMALL),
        ).pack(fill="x", pady=(0, 4))
        self.text_ingredientes = ctk.CTkTextbox(contenido, fg_color=theme.BG_INPUT, height=100)
        self.text_ingredientes.pack(fill="x", pady=(0, 12))
        if self.receta and self.receta.ingredientes:
            self.text_ingredientes.insert("1.0", self.receta.ingredientes)

        ctk.CTkLabel(contenido, text="Pasos rápidos (uno por línea)", anchor="w").pack(fill="x")
        self.text_pasos = ctk.CTkTextbox(contenido, fg_color=theme.BG_INPUT, height=100)
        self.text_pasos.pack(fill="x", pady=(0, 12))
        if self.receta and self.receta.pasos:
            self.text_pasos.insert("1.0", self.receta.pasos)

        self.label_error = ctk.CTkLabel(contenido, text="", text_color=theme.ERROR, wraplength=380, justify="left")
        self.label_error.pack(fill="x")

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
        ingredientes = self.text_ingredientes.get("1.0", "end")
        pasos = self.text_pasos.get("1.0", "end")
        try:
            if self.receta:
                recetas.actualizar_receta(
                    self.receta.id, nombre, url, miniatura_manual=self.ruta_miniatura_manual,
                    ingredientes=ingredientes, pasos=pasos,
                )
            else:
                recetas.crear_receta(
                    nombre, url, creado_por=self.current_user.id, miniatura_manual=self.ruta_miniatura_manual,
                    ingredientes=ingredientes, pasos=pasos,
                )
        except recetas.ValidationError as e:
            self.label_error.configure(text=str(e))
            return
        self.on_guardado()
        self.destroy()


class ConfirmarQuitarReceta(ctk.CTkToplevel):
    def __init__(self, master, receta, on_confirmado):
        super().__init__(master)
        self.receta = receta
        self.on_confirmado = on_confirmado

        self.title("Quitar receta")
        self.geometry("360x200")
        self.configure(fg_color=theme.BG_PAGE)
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self, text=f'¿Quitar la receta de "{receta.nombre_producto}"? Esta acción no se puede deshacer.',
            wraplength=310, justify="left",
        ).pack(fill="x", padx=24, pady=(24, 16))

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            botones, text="Cancelar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            botones, text="Sí, Quitar", fg_color=theme.ERROR, hover_color=theme.ERROR,
            text_color="#FFFFFF", corner_radius=theme.RADIUS_BUTTON, command=self._Quitar,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def _Quitar(self):
        recetas.Quitar_receta(self.receta.id)
        self.destroy()
        self.on_confirmado()
