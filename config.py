"""Configuración global de la aplicación."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "pos.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
ASSETS_DIR = BASE_DIR / "assets"

# Datos del negocio (se usan en encabezados de UI y, más adelante, en el ticket impreso)
NEGOCIO_NOMBRE = "Cuillas"
NEGOCIO_SUBTITULO = "Bebidas, crepas y waffles"

# Ventana principal
VENTANA_ANCHO = 1200
VENTANA_ALTO = 750

# Ticket impreso (Fase 4) — Epson TM-T20III conectada por USB.
# TICKET_USB_VENDOR_ID / TICKET_USB_PRODUCT_ID quedan en None hasta que la
# impresora esté conectada: mientras tanto, imprimir_venta() falla con un
# mensaje claro y la app sigue funcionando en modo de vista previa (texto).
#
# Para obtenerlos en Mac, con la impresora conectada por USB, corre:
#   system_profiler SPUSBDataType | grep -B 5 -i "epson\|tm-t20"
# y busca las líneas "Vendor ID" y "Product ID" del dispositivo.
TICKET_USB_VENDOR_ID = None
TICKET_USB_PRODUCT_ID = None

TICKET_MENSAJE_DESPEDIDA = "¡Gracias por tu compra! Vuelve pronto"
