"""Ajusta el tamaño de una ventana emergente (CTkToplevel) para que nunca
quede más grande que la pantalla real y se centre — en un monitor
táctil de POS (sin mouse para mover o redimensionar) una ventana de
tamaño fijo que se sale de la pantalla deja botones como "Guardar" o
"Agregar" fuera de alcance, sin ninguna forma de llegar a ellos."""

MARGEN_ANCHO = 40
MARGEN_ALTO = 80


def ajustar_geometria(toplevel, ancho_deseado, alto_deseado):
    ancho_pantalla = toplevel.winfo_screenwidth()
    alto_pantalla = toplevel.winfo_screenheight()
    ancho = min(ancho_deseado, ancho_pantalla - MARGEN_ANCHO)
    alto = min(alto_deseado, alto_pantalla - MARGEN_ALTO)
    x = max(0, (ancho_pantalla - ancho) // 2)
    y = max(0, (alto_pantalla - alto) // 2)
    toplevel.geometry(f"{ancho}x{alto}+{x}+{y}")
