from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pdftool.core.config import data_dir

_LOGGER_NAME = "pdftool"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_DOC_EXT = r"pdf|jpe?g|png"

# Redacción por capas, aplicadas EN ORDEN sobre el texto ya formateado
# (incluye tracebacks). El orden importa:
#   1) rutas/archivos entre comillas simples primero: los mensajes de
#      excepción suelen citarlas y las comillas delimitan nombres con
#      espacios que un patrón sin comillas no podría acotar.
#   2) rutas sin comillas, consumiendo la ruta COMPLETA (no solo el
#      segmento de usuario) para no dejar carpetas/nombres de archivo tras
#      el "~".
#   3) nombres de archivo de documento sueltos (sin ruta ni comillas),
#      incluida la cola de un nombre partido por espacios.
_REDACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # 1) rutas o nombres citados
    (re.compile(r"'[^'\n]*[/\\][^'\n]*'"), "'[ruta]'"),
    (re.compile(rf"'[^'\n]*\.({_DOC_EXT})'", re.IGNORECASE), "'[archivo]'"),
    # 2) rutas completas sin comillas
    (re.compile(re.escape(str(Path.home())) + r"\S*"), "~"),
    (re.compile(r"/Users/\S+"), "~"),
    (re.compile(r"[A-Za-z]:[\\/]Users[\\/]\S+"), "~"),
    # 3) nombres de archivo sueltos (sin ruta)
    (re.compile(rf"\S+\.({_DOC_EXT})\b", re.IGNORECASE), "[archivo]"),
]


def sanitize(text: str) -> str:
    """Redacta rutas y nombres de documentos personales de cualquier texto.

    Aplica las capas de `_REDACTION_PATTERNS` en orden: primero lo citado
    entre comillas, luego rutas completas sin comillas, y por último
    nombres de archivo de documento sueltos. Ninguna capa debe dejar
    filtrar carpetas ni nombres de archivo del usuario.
    """
    for pattern, replacement in _REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class _SanitizingFormatter(logging.Formatter):
    """Sanitiza la línea completa ya formateada (cubre también el traceback)."""

    def format(self, record: logging.LogRecord) -> str:
        return sanitize(super().format(record))


def log_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_paths() -> list[Path]:
    """Archivos de log existentes, backup primero (orden cronológico)."""
    base = log_dir() / "pdf-tool.log"
    backup = base.parent / (base.name + ".1")  # como lo nombra RotatingFileHandler
    return [p for p in (backup, base) if p.exists()]


def setup_logging() -> None:
    """Configura el logger "pdftool" una sola vez (idempotente)."""
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    logger.propagate = False  # sin ruido de/para el root (pymupdf, flet)
    handler = RotatingFileHandler(log_dir() / "pdf-tool.log", maxBytes=512_000,
                                  backupCount=1, encoding="utf-8")
    handler.setFormatter(_SanitizingFormatter(_FORMAT))
    logger.addHandler(handler)
