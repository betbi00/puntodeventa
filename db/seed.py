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
    """Ingredientes de crepa/waffle + boba + perlas explosivas, con stock de
    ejemplo. Los ingredientes del armador guiado (categoria_armado) siguen
    el menú oficial: base, fruta, complemento y decoración."""
    existentes = conn.execute("SELECT COUNT(*) FROM insumos").fetchone()[0]
    if existentes > 0:
        return

    # (nombre, aplica_a, categoria_armado, precio_extra, stock, stock_min)
    ingredientes = [
        ("Nutella", "ambos", "base", 15.0, 25, 5),
        ("Philadelphia", "ambos", "base", 10.0, 15, 5),
        ("Fresa", "ambos", "fruta", 8.0, 20, 5),
        ("Plátano", "ambos", "fruta", 6.0, 20, 5),
        ("Durazno", "ambos", "fruta", 0.0, 20, 5),  # precio pendiente de definir
        ("Lechera", "ambos", "complemento", 8.0, 20, 5),
        ("Azúcar glass", "ambos", "decoracion", 0.0, 20, 5),  # precio pendiente de definir
        # Ya no están en el menú oficial, pero se conservan en inventario
        # (sin categoria_armado: no aparecen en el armador de Crepa/Waffle).
        ("Cajeta", "ambos", None, 10.0, 20, 5),
        ("Helado de vainilla", "ambos", None, 18.0, 15, 5),
        ("Chispas de chocolate", "ambos", None, 7.0, 25, 8),
        ("Coco rallado", "ambos", None, 6.0, 15, 5),
        ("Nuez picada", "ambos", None, 12.0, 15, 5),
    ]
    for nombre, aplica_a, categoria_armado, precio_extra, stock, stock_min in ingredientes:
        conn.execute(
            """INSERT INTO insumos
               (nombre, tipo, aplica_a, categoria_armado, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES (?, 'ingrediente', ?, ?, ?, 'porcion', ?, ?)""",
            (nombre, aplica_a, categoria_armado, precio_extra, stock, stock_min),
        )

    # Pulpas para el Frappé de agua con pulpa de fruta — tipo='pulpa' (no
    # 'ingrediente'), es el extra de elección única que se ofrece al
    # agregar esa bebida al carrito (ver bebidas.tipo_extra).
    pulpas = ["Pulpa de maracuyá", "Pulpa de mango", "Pulpa de fresa"]
    for nombre in pulpas:
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES (?, 'pulpa', 'ambos', 0, 'porcion', 20, 5)""",
            (nombre,),
        )

    # (nombre, tipo, stock, stock_min, activo) — las perlas explosivas ya no
    # están en el menú oficial de Bobas, se siembran desactivadas.
    extras_bebida = [
        ("Boba", "boba", 40, 10, 1),
        ("Perlas explosivas", "perla_explosiva", 25, 8, 0),
    ]
    for nombre, tipo, stock, stock_min, activo in extras_bebida:
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo, activo)
               VALUES (?, ?, 'ambos', 0, 'porcion', ?, ?, ?)""",
            (nombre, tipo, stock, stock_min, activo),
        )


def seed_bebidas(conn: sqlite3.Connection) -> None:
    """Bobas y Frappés del menú oficial. Las Bobas ya tienen precio; los
    Frappés todavía no (se siembran inactivos, con precio de $1.00 como
    marcador claro de "falta definir", hasta que el negocio los dé de alta
    con su precio real)."""
    existentes = conn.execute("SELECT COUNT(*) FROM bebidas").fetchone()[0]
    if existentes > 0:
        return

    # (nombre, precio, tipo_extra, stock, stock_min, activo)
    bebidas = [
        ("Boba Taro", 65.0, "boba_perlas", 20, 5, 1),
        ("Boba Matcha", 70.0, "boba_perlas", 20, 5, 1),
        ("Boba Chai", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé Taro", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé Matcha", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé Chai", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé Oreo", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé Mazapán", 1.0, "boba_perlas", 20, 5, 0),
        ("Frappé de agua con pulpa de fruta", 1.0, "pulpa", 20, 5, 0),
    ]
    for nombre, precio, tipo_extra, stock, stock_min, activo in bebidas:
        conn.execute(
            "INSERT INTO bebidas (nombre, precio, tipo_extra, stock_actual, stock_minimo, activo) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, precio, tipo_extra, stock, stock_min, activo),
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


def _insumo_existe(conn: sqlite3.Connection, nombre: str) -> bool:
    return conn.execute("SELECT 1 FROM insumos WHERE nombre = ?", (nombre,)).fetchone() is not None


def _bebida_existe(conn: sqlite3.Connection, nombre: str) -> bool:
    return conn.execute("SELECT 1 FROM bebidas WHERE nombre = ?", (nombre,)).fetchone() is not None


def actualizar_menu_oficial(conn: sqlite3.Connection) -> None:
    """A diferencia de seed_insumos/seed_bebidas (que solo siembran una
    base de datos vacía), esto ajusta un catálogo que ya tenía datos para
    que coincida con el menú oficial que dio el negocio — se ejecuta en
    cada arranque y cada paso valida si ya se aplicó antes, para poder
    correrse las veces que sea sin duplicar ni repetir nada."""
    # --- Insumos: renombrar y clasificar por paso del armado guiado ---
    if _insumo_existe(conn, "Queso crema") and not _insumo_existe(conn, "Philadelphia"):
        conn.execute(
            "UPDATE insumos SET nombre = 'Philadelphia', aplica_a = 'ambos', categoria_armado = 'base' "
            "WHERE nombre = 'Queso crema'"
        )

    for nombre, categoria_armado in (
        ("Nutella", "base"), ("Fresa", "fruta"), ("Plátano", "fruta"), ("Lechera", "complemento"),
    ):
        conn.execute(
            "UPDATE insumos SET categoria_armado = ? WHERE nombre = ? AND categoria_armado IS NULL",
            (categoria_armado, nombre),
        )

    if not _insumo_existe(conn, "Durazno"):
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, categoria_armado, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES ('Durazno', 'ingrediente', 'ambos', 'fruta', 0, 'porcion', 20, 5)"""
        )
    if not _insumo_existe(conn, "Azúcar glass"):
        conn.execute(
            """INSERT INTO insumos (nombre, tipo, aplica_a, categoria_armado, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES ('Azúcar glass', 'ingrediente', 'ambos', 'decoracion', 0, 'porcion', 20, 5)"""
        )
    for nombre in ("Pulpa de maracuyá", "Pulpa de mango", "Pulpa de fresa"):
        if not _insumo_existe(conn, nombre):
            conn.execute(
                """INSERT INTO insumos (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo)
                   VALUES (?, 'pulpa', 'ambos', 0, 'porcion', 20, 5)""",
                (nombre,),
            )
        else:
            # Estas pulpas se sembraron una vez como tipo='ingrediente'
            # antes de existir el tipo 'pulpa' — se corrige sin tocar el
            # precio (por si un administrador ya le puso uno).
            conn.execute(
                "UPDATE insumos SET tipo = 'pulpa' WHERE nombre = ? AND tipo = 'ingrediente'", (nombre,)
            )

    conn.execute("UPDATE insumos SET activo = 0 WHERE nombre = 'Perlas explosivas' AND activo = 1")

    # --- Bebidas: renombrar Bobas, agregar Frappés, desactivar lo que ya no está ---
    if _bebida_existe(conn, "Taro Milk Tea") and not _bebida_existe(conn, "Boba Taro"):
        conn.execute("UPDATE bebidas SET nombre = 'Boba Taro' WHERE nombre = 'Taro Milk Tea'")
    if _bebida_existe(conn, "Matcha Latte") and not _bebida_existe(conn, "Boba Matcha"):
        conn.execute("UPDATE bebidas SET nombre = 'Boba Matcha' WHERE nombre = 'Matcha Latte'")

    # (nombre, tipo_extra) — 'boba_perlas' para las Bobas y la mayoría de
    # Frappés, 'pulpa' solo para el Frappé de agua con pulpa de fruta.
    nuevas_bebidas = [
        ("Boba Chai", "boba_perlas"), ("Frappé Taro", "boba_perlas"), ("Frappé Matcha", "boba_perlas"),
        ("Frappé Chai", "boba_perlas"), ("Frappé Oreo", "boba_perlas"), ("Frappé Mazapán", "boba_perlas"),
        ("Frappé de agua con pulpa de fruta", "pulpa"),
    ]
    for nombre, tipo_extra in nuevas_bebidas:
        if not _bebida_existe(conn, nombre):
            conn.execute(
                "INSERT INTO bebidas (nombre, precio, tipo_extra, stock_actual, stock_minimo, activo) "
                "VALUES (?, 1.0, ?, 20, 5, 0)",
                (nombre, tipo_extra),
            )
        else:
            # Ya existía de una corrida anterior de esta migración (de
            # antes de que existiera tipo_extra) — se le asigna sin pisar
            # ningún valor que ya tuviera.
            conn.execute(
                "UPDATE bebidas SET tipo_extra = ? WHERE nombre = ? AND tipo_extra IS NULL",
                (tipo_extra, nombre),
            )

    # A las Bobas que ya existían desde antes (Boba Taro/Matcha, renombradas
    # arriba) también se les asigna su tipo de extra, sin pisar si ya tuvieran uno.
    for nombre in ("Boba Taro", "Boba Matcha"):
        conn.execute(
            "UPDATE bebidas SET tipo_extra = 'boba_perlas' WHERE nombre = ? AND tipo_extra IS NULL", (nombre,)
        )

    for nombre in ("Mango Tea", "Café Boba", "Brown Sugar Milk", "Chocolate Milk Tea"):
        conn.execute("UPDATE bebidas SET activo = 0 WHERE nombre = ? AND activo = 1", (nombre,))


def seed_all(conn: sqlite3.Connection) -> None:
    seed_usuarios(conn)
    seed_insumos(conn)
    seed_bebidas(conn)
    seed_productos_base(conn)
    seed_recetas(conn)
