from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.naming import unique_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.images2pdf.params import ImagesToPdfParams

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def output_path_for_images(input_path: Path, out_dir: Path | None = None) -> Path:
    """`<imagen>.pdf` en el destino (o junto al original), sin pisar nada."""
    p = Path(input_path)
    carpeta = Path(out_dir) if out_dir is not None else p.parent
    return unique_path(carpeta / f"{p.stem}.pdf")


def _convert_one(
    input_path: Path, progress: Progress, out_dir: Path | None = None
) -> tuple[Path, str]:
    """Convierte una imagen. Devuelve (salida, etiqueta); un error lanza."""
    if input_path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("Formato no soportado (usa JPG o PNG).")
    progress(0.0, "Convirtiendo imagen…")
    out = output_path_for_images(input_path, out_dir)
    # convert_to_pdf genera una página del tamaño exacto de la imagen.
    with fitz.open(str(input_path)) as img:
        pdf_bytes = img.convert_to_pdf()
    with atomic_output(out) as temporary:
        with fitz.open("pdf", pdf_bytes) as pdf:
            pdf.save(str(temporary), garbage=4, deflate=True)
    progress(1.0, "Listo")
    return out, f"→ {out.name}"


def images_to_pdf(
    inputs: list[Path], params: ImagesToPdfParams, progress: Progress = noop_progress
) -> ToolResult:
    batch = run_batch(
        inputs,
        lambda path, scoped: _convert_one(path, scoped, params.output_dir),
        progress,
        all_failed="Ninguna imagen pudo convertirse.",
    )
    outputs, total = batch.outputs, batch.total

    if total == 1:
        return ToolResult(
            outputs=outputs, summary=f"Imagen convertida → {outputs[0].name}"
        )

    progress(1.0, "Listo")
    if len(outputs) == total:
        summary = f"{total} imágenes convertidas"
    else:
        summary = f"{len(outputs)} de {total} imágenes convertidas"
    return ToolResult(outputs=outputs, summary=summary, items=batch.items)
