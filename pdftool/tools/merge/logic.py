from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.merge.params import MergeParams


def _noop(_p: float, _m: str) -> None:
    pass


def output_path_for_merge(inputs: list[Path]) -> Path:
    """Salida junto al primer PDF, `<primero>_merged.pdf`, sin colisionar con ninguna entrada."""
    first = Path(inputs[0])
    inputs_set = {Path(p) for p in inputs}
    candidate = first.parent / f"{first.stem}_merged.pdf"
    n = 1
    while candidate in inputs_set:
        candidate = first.parent / f"{first.stem}_merged_{n}.pdf"
        n += 1
    return candidate


def merge(inputs: list[Path], params: MergeParams,
          progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")

    paths = [Path(p) for p in inputs]
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(p)

    out = output_path_for_merge(paths)
    total = len(paths)
    progress(0.0, f"Uniendo {total} PDFs…")

    with fitz.open() as out_doc:
        for i, p in enumerate(paths):
            with fitz.open(str(p)) as src:
                out_doc.insert_pdf(src)
            progress((i + 1) / (total + 1), f"Añadido {p.name}")
        out_doc.save(str(out), garbage=4, deflate=True)

    progress(1.0, f"Listo: {out.name}")
    return ToolResult(outputs=[out], summary=f"{total} PDFs unidos → {out.name}")
