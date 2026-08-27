"""Inicialización de la base de datos: aplica pequeñas migraciones para
bases ya existentes, crea el esquema, y siembra datos de ejemplo."""
from config import SCHEMA_PATH
from db.connection import get_connection
from db.seed import seed_all

# (tabla, columna, definición SQL de la columna) — para columnas nuevas
# agregadas a tablas que ya existían en bases creadas antes de este cambio.
# CREATE TABLE IF NOT EXISTS no altera tablas ya existentes, así que estas
# columnas necesitan agregarse a mano si todavía no están. Deben aplicarse
# ANTES de correr schema.sql: si una tabla vieja no tiene la columna,
# los CREATE INDEX del esquema fallarían al intentar indexarla.
MIGRACIONES_COLUMNAS = [
    ("ventas", "promocion_id", "INTEGER REFERENCES promociones(id)"),
    ("recetas", "ingredientes", "TEXT"),
    ("recetas", "pasos", "TEXT"),
    ("bebidas", "stock_actual", "REAL NOT NULL DEFAULT 0"),
    ("bebidas", "stock_minimo", "REAL NOT NULL DEFAULT 0"),
    ("recetas", "imagen_pasos_path", "TEXT"),
]


def _tabla_existe(conn, tabla: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (tabla,)
    ).fetchone()
    return row is not None


def _aplicar_migraciones_columnas(conn) -> None:
    for tabla, columna, definicion in MIGRACIONES_COLUMNAS:
        if not _tabla_existe(conn, tabla):
            continue  # tabla nueva: schema.sql ya la crea con la columna incluida
        columnas_existentes = {row["name"] for row in conn.execute(f"PRAGMA table_info({tabla})")}
        if columna not in columnas_existentes:
            conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")


def _migrar_check_insumos_tipo(conn) -> None:
    """SQLite no permite modificar un CHECK constraint con ALTER TABLE: si
    la tabla insumos ya existe con la restricción vieja (sin 'desechable'),
    hay que reconstruirla — renombrar, crear de nuevo con el esquema
    actual, copiar los datos, y borrar la vieja. Se desactivan las llaves
    foráneas mientras dura la reconstrucción para no chocar con las filas
    de detalle_venta_insumos/movimientos_inventario que ya apuntan a estos
    insumos."""
    if not _tabla_existe(conn, "insumos"):
        return  # tabla nueva: schema.sql ya la crea con el CHECK actualizado

    definicion = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'insumos'"
    ).fetchone()["sql"]
    if "desechable" in definicion:
        return  # ya está actualizada

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("ALTER TABLE insumos RENAME TO insumos_viejo")
        conn.execute("""
            CREATE TABLE insumos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre          TEXT NOT NULL,
                tipo            TEXT NOT NULL CHECK (tipo IN ('ingrediente', 'boba', 'perla_explosiva', 'desechable')),
                aplica_a        TEXT CHECK (aplica_a IN ('crepa', 'waffle', 'ambos')) DEFAULT 'ambos',
                precio_extra    REAL NOT NULL DEFAULT 0,
                unidad_medida   TEXT NOT NULL DEFAULT 'pza',
                stock_actual    REAL NOT NULL DEFAULT 0,
                stock_minimo    REAL NOT NULL DEFAULT 0,
                activo          INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            INSERT INTO insumos (id, nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo, activo)
            SELECT id, nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo, activo
            FROM insumos_viejo
        """)
        conn.execute("DROP TABLE insumos_viejo")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _migrar_movimientos_inventario_bebida(conn) -> None:
    """Antes, movimientos_inventario solo podía apuntar a un insumo
    (insumo_id NOT NULL). Ahora también necesita poder apuntar a una
    bebida (para llevar el stock de bebidas con su propia bitácora), así
    que insumo_id debe volverse opcional y se agrega bebida_id — un
    cambio de CHECK/NOT NULL que SQLite no permite con ALTER TABLE, por lo
    que se reconstruye la tabla igual que con insumos.tipo."""
    if not _tabla_existe(conn, "movimientos_inventario"):
        return  # tabla nueva: schema.sql ya la crea con bebida_id incluido

    definicion = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'movimientos_inventario'"
    ).fetchone()["sql"]
    if "bebida_id" in definicion:
        return  # ya está actualizada

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("ALTER TABLE movimientos_inventario RENAME TO movimientos_inventario_viejo")
        conn.execute("""
            CREATE TABLE movimientos_inventario (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                insumo_id           INTEGER REFERENCES insumos(id),
                bebida_id           INTEGER REFERENCES bebidas(id),
                tipo                TEXT NOT NULL CHECK (tipo IN ('entrada', 'ajuste', 'venta')),
                cantidad            REAL NOT NULL,
                stock_resultante    REAL NOT NULL,
                motivo              TEXT,
                usuario_id          INTEGER NOT NULL REFERENCES usuarios(id),
                referencia_venta_id INTEGER REFERENCES ventas(id),
                fecha_hora          TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                CHECK ((insumo_id IS NOT NULL AND bebida_id IS NULL) OR (insumo_id IS NULL AND bebida_id IS NOT NULL))
            )
        """)
        conn.execute("""
            INSERT INTO movimientos_inventario
                (id, insumo_id, tipo, cantidad, stock_resultante, motivo, usuario_id, referencia_venta_id, fecha_hora)
            SELECT id, insumo_id, tipo, cantidad, stock_resultante, motivo, usuario_id, referencia_venta_id, fecha_hora
            FROM movimientos_inventario_viejo
        """)
        conn.execute("DROP TABLE movimientos_inventario_viejo")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _migrar_recetas_quitar_video(conn) -> None:
    """El negocio dejó de usar videos de YouTube para las recetas (se
    tarda más grabar/ver el video que memorizar el paso a paso), así que
    video_url/video_id/miniatura_path ya no se usan — se reemplazan por
    imagen_pasos_path (agregada arriba en MIGRACIONES_COLUMNAS). SQLite
    3.35+ sí permite DROP COLUMN directo, sin necesitar reconstruir la
    tabla como con un CHECK."""
    if not _tabla_existe(conn, "recetas"):
        return  # tabla nueva: schema.sql ya la crea sin estas columnas

    columnas_existentes = {row["name"] for row in conn.execute("PRAGMA table_info(recetas)")}
    for columna in ("video_url", "video_id", "miniatura_path"):
        if columna in columnas_existentes:
            conn.execute(f"ALTER TABLE recetas DROP COLUMN {columna}")


def initialize_database() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        _aplicar_migraciones_columnas(conn)
        _migrar_check_insumos_tipo(conn)
        _migrar_movimientos_inventario_bebida(conn)
        _migrar_recetas_quitar_video(conn)
        conn.executescript(schema_sql)
        seed_all(conn)
