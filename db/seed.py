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


def seed_insumos(conn: sqlite3.Connection) -> None:
    """Ingredientes de crepa/waffle + boba + perlas explosivas, con stock de ejemplo."""
    existentes = conn.execute("SELECT COUNT(*) FROM insumos").fetchone()[0]
    if existentes > 0:
        return

    ingredientes = [
        ("Nutella", "ambos", 15.0, 25, 5),
        ("Fresa", "ambos", 8.0, 20, 5),
        ("Plátano", "ambos", 6.0, 20, 5),
        ("Cajeta", "ambos", 10.0, 20, 5),
        ("Lechera", "ambos", 8.0, 20, 5),
        ("Helado de vainilla", "ambos", 18.0, 15, 5),
        ("Chispas de chocolate", "ambos", 7.0, 25, 8),
        ("Coco rallado", "ambos", 6.0, 15, 5),
        ("Nuez picada", "ambos", 12.0, 15, 5),
        ("Queso crema", "crepa", 10.0, 15, 5),
    ]
    for nombre, aplica_a, precio_extra, stock, stock_min in ingredientes:
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES (?, 'ingrediente', ?, ?, 'porcion', ?, ?)""",
            (nombre, aplica_a, precio_extra, stock, stock_min),
        )

    extras_bebida = [
        ("Boba", "boba", 40, 10),
        ("Perlas explosivas", "perla_explosiva", 25, 8),
    ]
    for nombre, tipo, stock, stock_min in extras_bebida:
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES (?, ?, 'ambos', 0, 'porcion', ?, ?)""",
            (nombre, tipo, stock, stock_min),
        )


def seed_bebidas(conn: sqlite3.Connection) -> None:
    existentes = conn.execute("SELECT COUNT(*) FROM bebidas").fetchone()[0]
    if existentes > 0:
        return

    bebidas = [
        ("Taro Milk Tea", 65.0),
        ("Matcha Latte", 70.0),
        ("Mango Tea", 58.0),
        ("Café Boba", 60.0),
        ("Brown Sugar Milk", 62.0),
        ("Chocolate Milk Tea", 63.0),
    ]
    for nombre, precio in bebidas:
        conn.execute("INSERT INTO bebidas (nombre, precio) VALUES (?, ?)", (nombre, precio))


def seed_productos_base(conn: sqlite3.Connection) -> None:
    existentes = conn.execute("SELECT COUNT(*) FROM productos_base").fetchone()[0]
    if existentes > 0:
        return

    conn.execute("INSERT INTO productos_base (nombre, precio_base) VALUES ('Crepa', 45.0)")
    conn.execute("INSERT INTO productos_base (nombre, precio_base) VALUES ('Waffle', 50.0)")


def seed_all(conn: sqlite3.Connection) -> None:
    seed_usuarios(conn)
    seed_insumos(conn)
    seed_bebidas(conn)
    seed_productos_base(conn)
