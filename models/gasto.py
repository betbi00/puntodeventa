"""Modelo y acceso a datos de gastos del negocio (renta, agua, luz, etc.),
independientes de las ventas. No hay ninguna tabla que los referencie, así
que —igual que las recetas— se pueden eliminar de verdad."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Gasto:
    id: int
    concepto: str
    categoria: str
    monto: float
    fecha: str
    usuario_id: int
    notas: Optional[str]
    fecha_registro: str

    @staticmethod
    def from_row(row) -> "Gasto":
        return Gasto(
            id=row["id"],
            concepto=row["concepto"],
            categoria=row["categoria"],
            monto=row["monto"],
            fecha=row["fecha"],
            usuario_id=row["usuario_id"],
            notas=row["notas"],
            fecha_registro=row["fecha_registro"],
        )


def listar(desde: Optional[str] = None, hasta: Optional[str] = None, limite: Optional[int] = None) -> list[Gasto]:
    query = "SELECT * FROM gastos"
    condiciones = []
    params = []
    if desde:
        condiciones.append("fecha >= ?")
        params.append(desde)
    if hasta:
        condiciones.append("fecha <= ?")
        params.append(hasta)
    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)
    query += " ORDER BY fecha DESC, id DESC"
    if limite:
        query += " LIMIT ?"
        params.append(limite)
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Gasto.from_row(r) for r in rows]


def get_by_id(gasto_id: int) -> Optional[Gasto]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM gastos WHERE id = ?", (gasto_id,)).fetchone()
    return Gasto.from_row(row) if row else None


def crear(concepto: str, categoria: str, monto: float, fecha: str, usuario_id: int, notas: Optional[str]) -> Gasto:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO gastos (concepto, categoria, monto, fecha, usuario_id, notas)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (concepto, categoria, monto, fecha, usuario_id, notas),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar(gasto_id: int, concepto: str, categoria: str, monto: float, fecha: str, notas: Optional[str]) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE gastos SET concepto = ?, categoria = ?, monto = ?, fecha = ?, notas = ?
               WHERE id = ?""",
            (concepto, categoria, monto, fecha, notas, gasto_id),
        )


def eliminar(gasto_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id = ?", (gasto_id,))
