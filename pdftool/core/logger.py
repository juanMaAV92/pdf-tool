from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pdftool.core.config import data_dir

_LOGGER_NAME = "pdftool"
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Rutas personales en cualquier texto (mensajes de excepción incluidos).
_USER_PATH_PATTERNS = [
    re.compile(r"/Users/[^/\s]+"),                 # macOS
    re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+"),  # Windows
]


def sanitize(text: str) -> str:
    """Redacta rutas personales: home real y /Users|C:\\Users genéricos -> ~."""
    text = text.replace(str(Path.home()), "~")
    for pattern in _USER_PATH_PATTERNS:
        text = pattern.sub("~", text)
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
