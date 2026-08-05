"""Inicialización de la base de datos: crea el esquema y siembra datos de ejemplo."""
from config import SCHEMA_PATH
from db.connection import get_connection
from db.seed import seed_all


def initialize_database() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema_sql)
        seed_all(conn)
