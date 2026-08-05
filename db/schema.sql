-- Esquema completo del Punto de Venta.
-- Todas las tablas usan CREATE TABLE IF NOT EXISTS para poder ejecutarse
-- de forma segura en cada arranque de la aplicación.

CREATE TABLE IF NOT EXISTS usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    usuario         TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL CHECK (rol IN ('admin', 'vendedor')),
    activo          INTEGER NOT NULL DEFAULT 1,
    fecha_creacion  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Ingredientes de crepa/waffle + boba + perlas explosivas (inventario unificado)
CREATE TABLE IF NOT EXISTS insumos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('ingrediente', 'boba', 'perla_explosiva')),
    aplica_a        TEXT CHECK (aplica_a IN ('crepa', 'waffle', 'ambos')) DEFAULT 'ambos',
    precio_extra    REAL NOT NULL DEFAULT 0,
    unidad_medida   TEXT NOT NULL DEFAULT 'pza',
    stock_actual    REAL NOT NULL DEFAULT 0,
    stock_minimo    REAL NOT NULL DEFAULT 0,
    activo          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS productos_base (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE,
    precio_base     REAL NOT NULL,
    activo          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bebidas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    precio          REAL NOT NULL,
    activo          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ventas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora          TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(id),
    subtotal            REAL NOT NULL,
    descuento_pct       REAL NOT NULL DEFAULT 0,
    descuento_monto     REAL NOT NULL DEFAULT 0,
    total               REAL NOT NULL,
    metodo_pago         TEXT NOT NULL CHECK (metodo_pago IN ('efectivo', 'tarjeta')),
    mp_payment_id       TEXT,
    mp_status           TEXT,
    ticket_impreso      INTEGER NOT NULL DEFAULT 0,
    estado              TEXT NOT NULL DEFAULT 'completada' CHECK (estado IN ('completada', 'cancelada'))
);

CREATE TABLE IF NOT EXISTS detalle_venta (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id            INTEGER NOT NULL REFERENCES ventas(id) ON DELETE CASCADE,
    tipo_producto       TEXT NOT NULL CHECK (tipo_producto IN ('producto_base', 'bebida')),
    producto_base_id    INTEGER REFERENCES productos_base(id),
    bebida_id           INTEGER REFERENCES bebidas(id),
    nombre_producto     TEXT NOT NULL,
    precio_unitario     REAL NOT NULL,
    cantidad            INTEGER NOT NULL DEFAULT 1,
    subtotal_item       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS detalle_venta_insumos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    detalle_venta_id    INTEGER NOT NULL REFERENCES detalle_venta(id) ON DELETE CASCADE,
    insumo_id           INTEGER NOT NULL REFERENCES insumos(id),
    nombre_insumo       TEXT NOT NULL,
    precio_extra        REAL NOT NULL DEFAULT 0,
    cantidad_usada      REAL NOT NULL DEFAULT 1
);

-- Bitácora de movimientos de stock: entradas (restock), ajustes manuales
-- (correcciones de conteo) y descuentos por venta. Todo cambio de stock_actual
-- en insumos debe pasar por aquí para dejar rastro de quién, cuándo y por qué.
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    insumo_id           INTEGER NOT NULL REFERENCES insumos(id),
    tipo                TEXT NOT NULL CHECK (tipo IN ('entrada', 'ajuste', 'venta')),
    cantidad            REAL NOT NULL,
    stock_resultante    REAL NOT NULL,
    motivo              TEXT,
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(id),
    referencia_venta_id INTEGER REFERENCES ventas(id),
    fecha_hora          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS recetas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_producto     TEXT NOT NULL,
    video_url           TEXT NOT NULL,
    video_id            TEXT,
    miniatura_path      TEXT,
    creado_por          INTEGER REFERENCES usuarios(id),
    fecha_creacion      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_ventas_usuario ON ventas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_detalle_venta_venta ON detalle_venta(venta_id);
CREATE INDEX IF NOT EXISTS idx_detalle_insumos_detalle ON detalle_venta_insumos(detalle_venta_id);
CREATE INDEX IF NOT EXISTS idx_detalle_insumos_insumo ON detalle_venta_insumos(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_insumo ON movimientos_inventario(insumo_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos_inventario(fecha_hora);
