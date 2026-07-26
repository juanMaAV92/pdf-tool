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
                stem: str | None = None, out_dir: Path | None = None) -> Path:
    """`<stem>_<suffix>.pdf` junto al original, sin pisar nada.

    `stem` sobrescribe el del archivo de entrada (Comprimir lo usa para no
    acumular sufijos al reprocesar); `None` significa "usa el del archivo de
    entrada", pero una cadena vacía es un valor válido y se respeta tal cual.
    Es el único punto donde se decide dónde va una salida de nombre
    automático; `taken` garantiza que nunca sea la entrada, con independencia
    de lo que haya en disco.

    `out_dir` es `None` → junto al original; una ruta → todas las salidas van
    allí.

    `taken` solo cubre la propia entrada, no el resto de un lote: eso es
    seguro porque cada herramienta valida que todos los archivos de entrada
    existan en disco antes de calcular ninguna ruta de salida, y porque cada
    salida se escribe antes de resolver la siguiente ruta, así que
    `unique_path` ya la ve en disco.
    """
    p = Path(input_path)
    carpeta = Path(out_dir) if out_dir is not None else p.parent
    stem_final = stem if stem is not None else p.stem
    return unique_path(carpeta / f"{stem_final}_{suffix}.pdf", taken=(p,))
