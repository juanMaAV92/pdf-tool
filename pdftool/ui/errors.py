from __future__ import annotations

from pdftool.core.errors import user_message


def humanize_error(exc: Exception) -> tuple[str, str | None]:
    """Traduce una excepción a (mensaje para el usuario, detalle técnico | None).

    La regla vive en `core.errors` para que la lógica por lotes la aplique
    también a cada archivo; aquí solo se expone a la UI.
    """
    return user_message(exc)
