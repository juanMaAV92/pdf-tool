"""Bucle común de las herramientas por lote.

Un archivo que falla no detiene el lote: queda reportado en su `FileResult`.
La cancelación (`JobCancelled`) sí lo detiene, porque nunca se trata como un
fallo de archivo.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pdftool.core.jobs import JobCancelled
from pdftool.core.plugin import FileResult, Progress

# Procesa una entrada y devuelve (salida, mensaje corto para el usuario).
ProcessOne = Callable[[Path, Progress], tuple[Path, str]]


def noop_progress(_p: float, _m: str) -> None:
    pass


def validate_inputs(inputs: Sequence[Path | str]) -> list[Path]:
    """Normaliza las entradas y exige que haya al menos una y que existan."""
    if not inputs:
        raise ValueError("inputs está vacío")
    paths = [Path(p) for p in inputs]
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
    return paths


@dataclass
class BatchResult:
    outputs: list[Path]
    items: list[FileResult]

    @property
    def total(self) -> int:
        return len(self.items)


def run_batch(
    inputs: Sequence[Path | str],
    process_one: ProcessOne,
    progress: Progress = noop_progress,
    *,
    all_failed: str,
) -> BatchResult:
    """Procesa cada entrada aislando sus errores.

    Con un solo archivo, su error se relanza tal cual (así el mensaje humano
    del host lo reconoce). Con varios, solo se lanza `ValueError(all_failed)`
    si no salió ninguno.
    """
    paths = validate_inputs(inputs)
    total = len(paths)
    outputs: list[Path] = []
    items: list[FileResult] = []

    for index, path in enumerate(paths):

        def scoped(
            pct: float, msg: str, _i: int = index, _name: str = path.name
        ) -> None:
            label = f"[{_i + 1}/{total}] {_name}: {msg}" if total > 1 else msg
            progress((_i + pct) / total, label)

        try:
            out, message = process_one(path, scoped)
        except JobCancelled:
            raise
        except Exception as exc:  # este archivo falla; el lote continúa
            if total == 1:
                raise
            items.append(FileResult(path, None, False, str(exc)))
            continue
        outputs.append(out)
        items.append(FileResult(path, out, True, message))

    if not outputs:
        raise ValueError(all_failed)
    return BatchResult(outputs=outputs, items=items)
