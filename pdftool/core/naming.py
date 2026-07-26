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


def output_path(input_path: Path, suffix: str, *,
                stem: str | None = None) -> Path:
    """`<stem>_<suffix>.pdf` junto al original, sin pisar nada.

    `stem` sobrescribe el del archivo de entrada (Comprimir lo usa para no
    acumular sufijos al reprocesar). Es el único punto donde se decide dónde va
    una salida de nombre automático; `taken` garantiza que nunca sea la entrada,
    con independencia de lo que haya en disco.
    """
    p = Path(input_path)
    return unique_path(p.parent / f"{stem or p.stem}_{suffix}.pdf", taken=(p,))
