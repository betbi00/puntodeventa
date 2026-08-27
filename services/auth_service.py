"""Lógica de negocio de autenticación y gestión de usuarios."""
from models import usuario as usuario_model
from models.usuario import Usuario
from utils.security import hash_password, verificar_password

ROLES_VALIDOS = ("admin", "vendedor")


class AuthError(Exception):
    """Credenciales inválidas o usuario inactivo."""


class ValidationError(Exception):
    """Datos de entrada inválidos (usuario duplicado, rol inválido, etc.)."""


def login(usuario: str, password: str) -> Usuario:
    user = usuario_model.get_by_usuario(usuario.strip())
    if not user or not user.activo or not verificar_password(password, user.password_hash):
        raise AuthError("Usuario o contraseña incorrectos")
    return user


def crear_usuario(nombre: str, usuario: str, password: str, rol: str) -> Usuario:
    nombre = nombre.strip()
    usuario = usuario.strip()
    if not nombre or not usuario or not password:
        raise ValidationError("Nombre, usuario y contraseña son obligatorios")
    if rol not in ROLES_VALIDOS:
        raise ValidationError(f"Rol inválido: {rol}")
    if usuario_model.existe_usuario(usuario):
        raise ValidationError(f"El usuario '{usuario}' ya existe")
    return usuario_model.crear(nombre, usuario, hash_password(password), rol)


def resetear_password(usuario_id: int, nueva_password: str) -> None:
    if not nueva_password:
        raise ValidationError("La nueva contraseña no puede estar vacía")
    usuario_model.actualizar_password(usuario_id, hash_password(nueva_password))


def set_activo(usuario_id: int, activo: bool) -> None:
    usuario_model.set_activo(usuario_id, activo)


def actualizar_usuario(usuario_id: int, nombre: str, rol: str) -> None:
    if rol not in ROLES_VALIDOS:
        raise ValidationError(f"Rol inválido: {rol}")
    usuario_model.actualizar_datos(usuario_id, nombre.strip(), rol)


def listar_usuarios() -> list[Usuario]:
    return usuario_model.listar()
