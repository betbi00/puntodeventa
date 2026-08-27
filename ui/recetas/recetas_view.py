"""Vista de recetas: cada tarjeta muestra, lado a lado, la imagen del
paso a paso (grande, con botón para ampliarla a pantalla completa) y la
receta detallada (ingredientes y pasos) — todo visible de un vistazo, sin
tener que abrir nada. El administrador puede crear/editar/Quitar; el
vendedor solo ve (solo lectura)."""
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from services import receta_service as recetas
from ui import theme

TAMANO_IMAGEN_LISTA = (420, 300)
ANCHO_COLUMNA_IZQUIERDA = 440


def _imagen_ajustada(ruta, max_ancho, max_alto):
    """Abre la imagen y calcula un tamaño que quepa dentro de
    (max_ancho, max_alto) sin deformarla."""
    imagen = Image.open(ruta)
    escala = min(max_ancho / imagen.width, max_alto / imagen.height, 1)
    return imagen, (round(imagen.width * escala), round(imagen.height * escala))


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
        izquierda.pack(side="left", padx=(0, 16), fill="y")
        izquierda.pack_propagate(False)

        tiene_imagen = self._imagen_grande(izquierda, receta)
        if tiene_imagen:
            ctk.CTkButton(
                izquierda, text="Ampliar imagen", corner_radius=theme.RADIUS_BUTTON,
                fg_color=theme.BLUE_SOFT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BLUE,
                command=lambda r=receta: ImagenCompletaDialog(self, r),
            ).pack(fill="x", pady=(10, 0))

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

        ctk.CTkLabel(
            derecha, text=receta.nombre_producto, anchor="w",
            font=(theme.FONT_FAMILY, theme.FONT_SIZE_TITLE, "bold"),
        ).pack(fill="x", pady=(0, 12))

        if receta.lista_ingredientes:
            self._bloque_texto(derecha, "Ingredientes", receta.lista_ingredientes)
        self._bloque_texto(derecha, "Pasos", receta.lista_pasos, numerado=True)

    def _imagen_grande(self, master, receta) -> bool:
        """Devuelve True si sí había una imagen para mostrar."""
        if receta.imagen_pasos_path and Path(receta.imagen_pasos_path).exists():
            try:
                imagen, tamano = _imagen_ajustada(receta.imagen_pasos_path, *TAMANO_IMAGEN_LISTA)
                ctk_imagen = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=tamano)
                ctk.CTkLabel(master, image=ctk_imagen, text="").pack(expand=True)
                return True
            except Exception:
                pass
        ctk.CTkLabel(
            master, text="🖼  Sin imagen de pasos", fg_color=theme.BG_INPUT, corner_radius=theme.RADIUS_INPUT,
            width=TAMANO_IMAGEN_LISTA[0], height=TAMANO_IMAGEN_LISTA[1], font=(theme.FONT_FAMILY, 16),
            text_color=theme.TEXT_SECONDARY,
        ).pack(expand=True)
        return False

    def _bloque_texto(self, master, titulo, items, numerado=False):
        ctk.CTkLabel(
            master, text=titulo, anchor="w", font=(theme.FONT_FAMILY, theme.FONT_SIZE_BODY, "bold"),
        ).pack(fill="x", pady=(0, 6))

        if not items:
            ctk.CTkLabel(
                master, text="No especificado", anchor="w", text_color=theme.TEXT_SECONDARY,
            ).pack(fill="x", pady=3)
            ctk.CTkFrame(master, fg_color="transparent", height=8).pack()
            return

        for i, item in enumerate(items, start=1):
            prefijo = f"{i}. " if numerado else "•  "
            ctk.CTkLabel(
                master, text=prefijo + item, anchor="w", justify="left", wraplength=560,
            ).pack(fill="x", pady=3)

        ctk.CTkFrame(master, fg_color="transparent", height=8).pack()

    def _abrir_form_nuevo(self):
        FormularioReceta(self, receta=None, current_user=self.current_user, on_guardado=self._refrescar)

    def _abrir_form_editar(self, receta):
        FormularioReceta(self, receta=receta, current_user=self.current_user, on_guardado=self._refrescar)

    def _confirmar_Quitar(self, receta):
        ConfirmarQuitarReceta(self, receta, on_confirmado=self._refrescar)


class ImagenCompletaDialog(ctk.CTkToplevel):
    """Muestra la imagen de pasos ocupando casi toda la pantalla, para
    poder leerla de lejos en la barra sin acercarse a la pantalla."""

    def __init__(self, master, receta):
        super().__init__(master)
        self.title(receta.nombre_producto)
        self.configure(fg_color=theme.BG_PAGE)
        self.grab_set()

        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        margen = 80
        imagen, tamano = _imagen_ajustada(
            receta.imagen_pasos_path, ancho_pantalla - margen, alto_pantalla - margen - 60,
        )
        self.imagen_ctk = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=tamano)

        ancho_ventana = min(tamano[0] + 60, ancho_pantalla - 20)
        alto_ventana = min(tamano[1] + 120, alto_pantalla - 20)
        self.geometry(f"{ancho_ventana}x{alto_ventana}")

        ctk.CTkLabel(self, image=self.imagen_ctk, text="").pack(expand=True, padx=20, pady=(20, 8))
        ctk.CTkButton(
            self, text="Cerrar", fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BG_HOVER, corner_radius=theme.RADIUS_BUTTON, command=self.destroy,
        ).pack(fill="x", padx=20, pady=(0, 20))
        self.bind("<Escape>", lambda _e: self.destroy())


class FormularioReceta(ctk.CTkToplevel):
    def __init__(self, master, receta, current_user, on_guardado):
        super().__init__(master)
        self.receta = receta
        self.current_user = current_user
        self.on_guardado = on_guardado
        self.ruta_imagen_nueva = None

        self.title("Editar receta" if receta else "Nueva receta")
        self.geometry("460x680")
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

        ctk.CTkLabel(contenido, text="Imagen del paso a paso", anchor="w").pack(fill="x")
        self.label_imagen = ctk.CTkLabel(
            contenido,
            text=(Path(self.receta.imagen_pasos_path).name if self.receta and self.receta.imagen_pasos_path
                  else "Ninguna imagen seleccionada"),
            text_color=theme.TEXT_SECONDARY, anchor="w",
        )
        self.label_imagen.pack(fill="x", pady=(4, 4))
        ctk.CTkButton(
            contenido, text="Elegir imagen…", corner_radius=theme.RADIUS_BUTTON,
            fg_color=theme.BG_INPUT, text_color=theme.TEXT_PRIMARY, hover_color=theme.BG_HOVER,
            command=self._elegir_imagen,
        ).pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(contenido, text="Ingredientes (uno por línea)", anchor="w").pack(fill="x", pady=(0, 4))
        self.text_ingredientes = ctk.CTkTextbox(contenido, fg_color=theme.BG_INPUT, height=120)
        self.text_ingredientes.pack(fill="x", pady=(0, 12))
        if self.receta and self.receta.ingredientes:
            self.text_ingredientes.insert("1.0", self.receta.ingredientes)

        ctk.CTkLabel(contenido, text="Pasos (uno por línea)", anchor="w").pack(fill="x", pady=(0, 4))
        self.text_pasos = ctk.CTkTextbox(contenido, fg_color=theme.BG_INPUT, height=160)
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
            parent=self, title="Elegir imagen de pasos",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg")],
        )
        if ruta:
            self.ruta_imagen_nueva = ruta
            self.label_imagen.configure(text=Path(ruta).name)

    def _guardar(self):
        nombre = self.entry_nombre.get()
        ingredientes = self.text_ingredientes.get("1.0", "end")
        pasos = self.text_pasos.get("1.0", "end")
        try:
            if self.receta:
                recetas.actualizar_receta(
                    self.receta.id, nombre, imagen_pasos=self.ruta_imagen_nueva,
                    ingredientes=ingredientes, pasos=pasos,
                )
            else:
                recetas.crear_receta(
                    nombre, creado_por=self.current_user.id, imagen_pasos=self.ruta_imagen_nueva,
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
