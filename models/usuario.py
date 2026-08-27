"""Modelo y acceso a datos de usuarios."""
from dataclasses import dataclass
from typing import Optional

from db.connection import get_connection


@dataclass
class Usuario:
    id: int
    nombre: str
    usuario: str
    password_hash: str
    rol: str
    activo: bool
    fecha_creacion: str

    @staticmethod
    def from_row(row) -> "Usuario":
        return Usuario(
            id=row["id"],
            nombre=row["nombre"],
            usuario=row["usuario"],
            password_hash=row["password_hash"],
            rol=row["rol"],
            activo=bool(row["activo"]),
            fecha_creacion=row["fecha_creacion"],
        )


def get_by_usuario(usuario: str) -> Optional[Usuario]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
    return Usuario.from_row(row) if row else None


def get_by_id(usuario_id: int) -> Optional[Usuario]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
    return Usuario.from_row(row) if row else None


def listar(incluir_inactivos: bool = True) -> list[Usuario]:
    query = "SELECT * FROM usuarios"
    if not incluir_inactivos:
        query += " WHERE activo = 1"
    query += " ORDER BY nombre"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [Usuario.from_row(row) for row in rows]


def existe_usuario(usuario: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
    return row is not None


def crear(nombre: str, usuario: str, password_hash: str, rol: str) -> Usuario:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO usuarios (nombre, usuario, password_hash, rol) VALUES (?, ?, ?, ?)",
            (nombre, usuario, password_hash, rol),
        )
        nuevo_id = cursor.lastrowid
    return get_by_id(nuevo_id)


def actualizar_password(usuario_id: int, password_hash: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (password_hash, usuario_id),
        )


def set_activo(usuario_id: int, activo: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET activo = ? WHERE id = ?",
            (1 if activo else 0, usuario_id),
        )


def actualizar_datos(usuario_id: int, nombre: str, rol: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE usuarios SET nombre = ?, rol = ? WHERE id = ?",
            (nombre, rol, usuario_id),
        )
