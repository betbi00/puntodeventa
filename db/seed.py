"""Datos de ejemplo para poder probar la app sin capturar todo a mano."""
import sqlite3

from config import ASSETS_DIR
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
        ("Taro Milk Tea", 65.0, 20, 5),
        ("Matcha Latte", 70.0, 20, 5),
        ("Mango Tea", 58.0, 20, 5),
        ("Café Boba", 60.0, 20, 5),
        ("Brown Sugar Milk", 62.0, 20, 5),
        ("Chocolate Milk Tea", 63.0, 20, 5),
    ]
    for nombre, precio, stock, stock_min in bebidas:
        conn.execute(
            "INSERT INTO bebidas (nombre, precio, stock_actual, stock_minimo) VALUES (?, ?, ?, ?)",
            (nombre, precio, stock, stock_min),
        )


def seed_productos_base(conn: sqlite3.Connection) -> None:
    existentes = conn.execute("SELECT COUNT(*) FROM productos_base").fetchone()[0]
    if existentes > 0:
        return

    conn.execute("INSERT INTO productos_base (nombre, precio_base) VALUES ('Crepa', 45.0)")
    conn.execute("INSERT INTO productos_base (nombre, precio_base) VALUES ('Waffle', 50.0)")


def seed_recetas(conn: sqlite3.Connection) -> None:
    """Las 5 recetas del negocio (masa, crepas, waffles, frapés, boba), con
    su imagen de paso a paso (ya versionada en assets/recetas_imagenes/) y
    los pasos detallados que dio el negocio."""
    existentes = conn.execute("SELECT COUNT(*) FROM recetas").fetchone()[0]
    if existentes > 0:
        return

    imagenes_dir = ASSETS_DIR / "recetas_imagenes"
    recetas = [
        ("Masa", "5a08c93993af462fb02c7e863223f8c0.png", """Intégra 3 huevos dentro de un bowl
Vierte 200 ml de agua
Añade una tapa de vainilla
Añade los 100 gramos de harina integral y mezcla muy bien hasta que no haya grumos
Añade el restante de harina de trigo y mezcla muy bien
Ve añadiendo el restante de agua poco a poco hasta que la mezcla quede en la textura deseada
Añade la mantequilla derretida y mézclala
Vierte la mezcla dentro de un recipiente y mantenla en refrigeración"""),
        ("Crepas", "3b68d763c7984946a03b65eac2666061.png", """Vierte un cucharón de mezcla a la crepera
Dale la forma adecuada a la crepa
Dobla por la mitad la crepa
Añade la base elegida por el cliente
Añade la porción de fruta en el centro de la crepa
Cierra la crepa por ambos lados
Con cuidado pon la crepa sobre el empaque
Decora y entrega"""),
        ("Waffles", "55e87cc3225b4b7d83583e94e0f0ac91.png", """Vierte la mezcla para waffles dentro de la Wafflera
Añade la base por encima
Añade la fruta y los complementos bien esparcidos en la superficie del waffle"""),
        ("Frapés", "c6cab0b143ae4ec486e6d084e5f999c7.png", """Llena el vaso de hielos al tope
Añade los polvos base de la bebida
Añade ingredientes (en el caso del Frappe de Oreo y Mazapán)
Añade los líquidos (6 oz en total)
Licúa hasta obtener la textura
Vierte la mezcla en un vaso
Añade crema batida
Añade decoración"""),
        ("Boba", "2a47142fc3254635810400be6da44865.png", """Agrega dos cucharadas grandes de polvo
Mezcla hasta eliminar grumos con agua caliente
Agrega la tapioca
Rellena con la leche de la elección del cliente
Introduce el vaso dentro de la selladora
Entrega"""),
    ]
    for nombre, archivo, pasos in recetas:
        conn.execute(
            "INSERT INTO recetas (nombre_producto, imagen_pasos_path, pasos) VALUES (?, ?, ?)",
            (nombre, str(imagenes_dir / archivo), pasos),
        )


def seed_all(conn: sqlite3.Connection) -> None:
    seed_usuarios(conn)
    seed_insumos(conn)
    seed_bebidas(conn)
    seed_productos_base(conn)
    seed_recetas(conn)
