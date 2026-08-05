"""Modelo y acceso a datos de recetas.

A diferencia de usuarios/insumos/bebidas/productos_base, las recetas SÍ se
eliminan de verdad (no solo se desactivan): ninguna otra tabla las
referencia por llave foránea, así que no hay riesgo de romper el
historial de ventas al borrarlas.
"""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Receta:
    id: int
    nombre_producto: str
    video_url: str
    video_id: Optional[str]
    miniatura_path: Optional[str]
    creado_por: Optional[int]
    fecha_creacion: str

    @staticmethod
    def from_row(row) -> "Receta":
        return Receta(
            id=row["id"],
            nombre_producto=row["nombre_producto"],
            video_url=row["video_url"],
            video_id=row["video_id"],
            miniatura_path=row["miniatura_path"],
            creado_por=row["creado_por"],
            fecha_creacion=row["fecha_creacion"],
        )


def listar() -> list[Receta]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM recetas ORDER BY nombre_producto").fetchall()
    return [Receta.from_row(r) for r in rows]


def get_by_id(receta_id: int) -> Optional[Receta]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM recetas WHERE id = ?", (receta_id,)).fetchone()
    return Receta.from_row(row) if row else None


def crear(
    nombre_producto: str, video_url: str, video_id: Optional[str],
    miniatura_path: Optional[str], creado_por: int,
) -> Receta:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO recetas (nombre_producto, video_url, video_id, miniatura_path, creado_por)
               VALUES (?, ?, ?, ?, ?)""",
            (nombre_producto, video_url, video_id, miniatura_path, creado_por),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(
    receta_id: int, nombre_producto: str, video_url: str,
    video_id: Optional[str], miniatura_path: Optional[str],
) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE recetas
               SET nombre_producto = ?, video_url = ?, video_id = ?, miniatura_path = ?
               WHERE id = ?""",
            (nombre_producto, video_url, video_id, miniatura_path, receta_id),
        )


def eliminar(receta_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM recetas WHERE id = ?", (receta_id,))
