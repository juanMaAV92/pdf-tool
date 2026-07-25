from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def unique_path(candidate: Path, taken: Iterable[Path] = ()) -> Path:
    """Primera ruta libre a partir de `candidate`, con sufijo « (n)».

    Libre = no existe en disco y no está en `taken`. `taken` cubre rutas que
    aún no se han escrito (p. ej. los archivos de entrada de un lote).
    """
    candidate = Path(candidate)
    blocked = {Path(p) for p in taken}

    def is_free(p: Path) -> bool:
        return p not in blocked and not p.exists()

    if is_free(candidate):
        return candidate
    n = 1
    while True:
        alt = candidate.with_name(f"{candidate.stem} ({n}){candidate.suffix}")
        if is_free(alt):
            return alt
        n += 1
