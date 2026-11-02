from __future__ import annotations

import os
import shutil
import tempfile
import uuid
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
        prefix=".pdf-tool-", suffix=target.suffix, dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        yield temporary
        os.replace(temporary, target)
    finally:
        # Si el bloque falla, elimina el temporal; `missing_ok` también cubre
        # el caso exitoso, donde os.replace ya lo movió al destino final.
        temporary.unlink(missing_ok=True)


@contextmanager
def atomic_output_dir(target: Path) -> Iterator[Path]:
    """Llena una carpeta temporal junto al destino y publícala al terminar.

    Ante cualquier salida anómala, incluida la cancelación, no queda nada: ni
    el destino ni el temporal. No usa `mkdtemp` porque crea la carpeta con
    permisos 0700, que pasarían a la carpeta del usuario.
    """
    target = Path(target)
    temporary = target.parent / f".pdf-tool-{uuid.uuid4().hex}"
    temporary.mkdir()
    try:
        yield temporary
        os.rename(temporary, target)
    finally:
        # `exists` es falso en el caso exitoso: os.rename ya la movió.
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def atomic_copy(source: Path, target: Path) -> None:
    """Copia `source` sin dejar una salida parcial si la copia falla."""
    with atomic_output(target) as temporary:
        shutil.copy2(source, temporary)


def atomic_write_text(target: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Escribe texto y publica el archivo solo cuando la escritura termina."""
    with atomic_output(target) as temporary:
        temporary.write_text(text, encoding=encoding)
