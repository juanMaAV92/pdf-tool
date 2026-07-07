from __future__ import annotations

_FILE_NOT_FOUND = ("No se encontró el archivo. ¿Lo moviste o borraste? "
                   "Vuelve a elegirlo.")
_PERMISSION = ("No se pudo guardar el resultado. Cierra el archivo si lo "
               "tienes abierto e inténtalo de nuevo.")
_GENERIC = "No se pudo procesar el PDF. Puede estar dañado o protegido."


def humanize_error(exc: Exception) -> tuple[str, str | None]:
    """Traduce una excepción a (mensaje para el usuario, detalle técnico | None).

    Los ValueError de dominio ya vienen en español, así que pasan tal cual.
    FileNotFoundError y PermissionError (subclases de OSError) se comprueban
    antes del caso genérico. El resto muestra un mensaje amable y conserva el
    detalle técnico para diagnóstico (plegado en la UI).
    """
    if isinstance(exc, ValueError):
        return str(exc), None
    if isinstance(exc, FileNotFoundError):
        return _FILE_NOT_FOUND, None
    if isinstance(exc, PermissionError):
        return _PERMISSION, None
    return _GENERIC, f"{type(exc).__name__}: {exc}"
