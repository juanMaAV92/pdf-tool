"""Traducción de excepciones a mensajes para el usuario (sin Flet).

Solo `UserError` se muestra tal cual: es el canal de los mensajes de dominio,
ya escritos en español para el usuario. Cualquier otra excepción, incluido un
`ValueError` de una librería, recibe un mensaje genérico y conserva el detalle
técnico para diagnóstico.
"""

from __future__ import annotations

_FILE_NOT_FOUND = (
    "No se encontró el archivo. ¿Lo moviste o borraste? Vuelve a elegirlo."
)
_PERMISSION = (
    "No hay permiso para leer o guardar el archivo. Ciérralo si lo tienes "
    "abierto o elige otra carpeta en «Guardar en»."
)
GENERIC_MESSAGE = (
    "No se pudo procesar el archivo. Puede estar dañado o tener contraseña "
    "(puedes quitarla con «Proteger PDF»)."
)


class UserError(ValueError):
    """Error de dominio con un mensaje listo para mostrar al usuario."""


def user_message(exc: BaseException) -> tuple[str, str | None]:
    """(mensaje para el usuario, detalle técnico | None)."""
    if isinstance(exc, UserError):
        return str(exc), None
    if isinstance(exc, FileNotFoundError):
        return _FILE_NOT_FOUND, None
    if isinstance(exc, PermissionError):
        return _PERMISSION, None
    return GENERIC_MESSAGE, f"{type(exc).__name__}: {exc}"
