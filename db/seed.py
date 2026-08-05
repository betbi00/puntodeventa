"""Datos de ejemplo para poder probar la app sin capturar todo a mano."""
import sqlite3

from utils.security import hash_password


def seed_usuarios(conn: sqlite3.Connection) -> None:
    """Crea un admin y un vendedor de ejemplo si la tabla usuarios está vacía."""
    existentes = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if existentes > 0:
        return

    conn.execute(
        "INSERT INTO usuarios (nombre, usuario, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Administrador", "admin", hash_password("admin123"), "admin"),
    )
    conn.execute(
        "INSERT INTO usuarios (nombre, usuario, password_hash, rol) VALUES (?, ?, ?, ?)",
        ("Vendedor Demo", "vendedor", hash_password("vendedor123"), "vendedor"),
    )


def seed_all(conn: sqlite3.Connection) -> None:
    seed_usuarios(conn)
