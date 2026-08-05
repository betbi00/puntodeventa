"""Modelo y acceso a datos de insumos (ingredientes, boba, perlas explosivas)."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection

TIPOS_VALIDOS = ("ingrediente", "boba", "perla_explosiva")
APLICA_A_VALIDOS = ("crepa", "waffle", "ambos")


@dataclass
class Insumo:
    id: int
    nombre: str
    tipo: str
    aplica_a: str
    precio_extra: float
    unidad_medida: str
    stock_actual: float
    stock_minimo: float
    activo: bool

    @staticmethod
    def from_row(row) -> "Insumo":
        return Insumo(
            id=row["id"],
            nombre=row["nombre"],
            tipo=row["tipo"],
            aplica_a=row["aplica_a"],
            precio_extra=row["precio_extra"],
            unidad_medida=row["unidad_medida"],
            stock_actual=row["stock_actual"],
            stock_minimo=row["stock_minimo"],
            activo=bool(row["activo"]),
        )

    @property
    def bajo_stock_minimo(self) -> bool:
        return self.stock_actual < self.stock_minimo


def listar(tipo=None, incluir_inactivos: bool = True) -> list[Insumo]:
    """tipo puede ser un solo string ('ingrediente') o una lista/tupla
    ('boba', 'perla_explosiva') para filtrar por varios tipos a la vez."""
    query = "SELECT * FROM insumos"
    condiciones = []
    params = []
    if tipo:
        if isinstance(tipo, (list, tuple)):
            placeholders = ",".join("?" for _ in tipo)
            condiciones.append(f"tipo IN ({placeholders})")
            params.extend(tipo)
        else:
            condiciones.append("tipo = ?")
            params.append(tipo)
    if not incluir_inactivos:
        condiciones.append("activo = 1")
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY nombre"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Insumo.from_row(row) for row in rows]


def get_by_id(insumo_id: int) -> Optional[Insumo]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM insumos WHERE id = ?", (insumo_id,)).fetchone()
    return Insumo.from_row(row) if row else None


def crear(
    nombre: str, tipo: str, aplica_a: str, precio_extra: float,
    unidad_medida: str, stock_inicial: float, stock_minimo: float,
) -> Insumo:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO insumos
               (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_actual, stock_minimo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (nombre, tipo, aplica_a, precio_extra, unidad_medida, stock_inicial, stock_minimo),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar_datos(
    insumo_id: int, nombre: str, aplica_a: str, precio_extra: float,
    unidad_medida: str, stock_minimo: float,
) -> None:
    """Actualiza los datos descriptivos del insumo. No toca stock_actual:
    eso solo se modifica a través de movimientos_inventario."""
    with get_connection() as conn:
        conn.execute(
            """UPDATE insumos
               SET nombre = ?, aplica_a = ?, precio_extra = ?, unidad_medida = ?, stock_minimo = ?
               WHERE id = ?""",
            (nombre, aplica_a, precio_extra, unidad_medida, stock_minimo, insumo_id),
        )


def set_activo(insumo_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE insumos SET activo = ? WHERE id = ?", (1 if activo else 0, insumo_id)
        )
