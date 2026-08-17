from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_output
from pdftool.core.naming import unique_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.merge.params import MergeParams


def _noop(_p: float, _m: str) -> None:
    pass


def output_path_for_merge(inputs: list[Path], name: str | None = None,
                          out_dir: Path | None = None) -> Path:
    """Salida junto al primer PDF (o en el destino); `name` custom o `<primero>_merged`.

    Nunca pisa un archivo existente ni una de las entradas: si el nombre está
    ocupado, se usa «nombre (1).pdf», «nombre (2).pdf»… La UI consulta esta
    misma función para avisar del nombre final antes de ejecutar.

    Si `out_dir` es None, la salida va junto al primer PDF.
    """
    first = Path(inputs[0])
    base = name or f"{first.stem}_merged"
    carpeta = Path(out_dir) if out_dir is not None else first.parent
    return unique_path(carpeta / f"{base}.pdf", taken=inputs)


def merge(inputs: list[Path], params: MergeParams,
          progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")

    paths = [Path(p) for p in inputs]
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(p)

    out = output_path_for_merge(paths, params.output_name, params.output_dir)
    total = len(paths)
    progress(0.0, f"Uniendo {total} PDFs…")

    with atomic_output(out) as temporary:
        with fitz.open() as out_doc:
            for i, p in enumerate(paths):
                with fitz.open(str(p)) as src:
                    out_doc.insert_pdf(src)
                progress((i + 1) / (total + 1), f"Añadido {p.name}")
            out_doc.save(str(temporary), garbage=4, deflate=True)

    progress(1.0, f"Listo: {out.name}")
    return ToolResult(outputs=[out], summary=f"{total} PDFs unidos → {out.name}")
