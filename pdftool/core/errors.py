"""Traducción de excepciones a mensajes para el usuario (sin Flet).

Solo `UserError` se muestra tal cual: es el canal de los mensajes de dominio,
ya traducidos al idioma activo al crearse. Cualquier otra excepción, incluido un
`ValueError` de una librería, recibe un mensaje genérico y conserva el detalle
técnico para diagnóstico.
"""

from __future__ import annotations

from pdftool.i18n import t


def generic_message() -> str:
    """Mensaje para cualquier fallo que no sea un `UserError`."""
    return t("core.error.generic")


class UserError(ValueError):
    """Error de dominio con un mensaje listo para mostrar al usuario."""


def user_message(exc: BaseException) -> tuple[str, str | None]:
    """(mensaje para el usuario, detalle técnico | None)."""
    if isinstance(exc, UserError):
        return str(exc), None
    if isinstance(exc, FileNotFoundError):
        return t("core.error.file_not_found"), None
    if isinstance(exc, PermissionError):
        return t("core.error.permission"), None
    return generic_message(), f"{type(exc).__name__}: {exc}"
