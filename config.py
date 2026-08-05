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
