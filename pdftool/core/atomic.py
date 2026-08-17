from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def atomic_output(target: Path) -> Iterator[Path]:
    """Escribe una salida en el mismo directorio y publícala al terminar.

    El archivo final no se crea ni se reemplaza hasta que el bloque termina sin
    excepción. Al usar el mismo directorio, `os.replace` conserva la operación
    como un cambio atómico dentro del mismo sistema de archivos.
    """
    target = Path(target)
    fd, temporary_name = tempfile.mkstemp(
        prefix=".pdf-tool-", suffix=target.suffix, dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        yield temporary
        os.replace(temporary, target)
    finally:
        # Si el bloque falla, elimina el temporal; `missing_ok` también cubre
        # el caso exitoso, donde os.replace ya lo movió al destino final.
        temporary.unlink(missing_ok=True)


def atomic_copy(source: Path, target: Path) -> None:
    """Copia `source` sin dejar una salida parcial si la copia falla."""
    with atomic_output(target) as temporary:
        shutil.copy2(source, temporary)


def atomic_write_text(target: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Escribe texto y publica el archivo solo cuando la escritura termina."""
    with atomic_output(target) as temporary:
        temporary.write_text(text, encoding=encoding)
