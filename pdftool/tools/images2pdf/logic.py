from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.images2pdf.params import ImagesToPdfParams

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _noop(_p: float, _m: str) -> None:
    pass


def output_path_for_images(inputs: list[Path], name: str | None = None) -> Path:
    """`name` custom o `<primera imagen>`, junto al original, sin pisar un PDF
    existente."""
    first = Path(inputs[0])
    base = name or first.stem
    candidate = first.parent / f"{base}.pdf"
    n = 1
    while candidate.exists():
        candidate = first.parent / f"{base}_{n}.pdf"
        n += 1
    return candidate


def images_to_pdf(inputs: list[Path], params: ImagesToPdfParams,
                  progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")

    paths = [Path(p) for p in inputs]
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(p)
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"Formato no soportado: {p.name} (usa JPG o PNG)")

    out = output_path_for_images(paths, params.output_name)
    total = len(paths)
    progress(0.0, f"Convirtiendo {total} imágenes…")

    with fitz.open() as out_doc:
        for i, p in enumerate(paths):
            # convert_to_pdf genera una página del tamaño exacto de la imagen.
            with fitz.open(str(p)) as img:
                pdf_bytes = img.convert_to_pdf()
            with fitz.open("pdf", pdf_bytes) as img_pdf:
                out_doc.insert_pdf(img_pdf)
            progress((i + 1) / (total + 1), f"Añadida {p.name}")
        out_doc.save(str(out), garbage=4, deflate=True)

    progress(1.0, f"Listo: {out.name}")
    return ToolResult(outputs=[out], summary=f"{total} imágenes → {out.name}")
