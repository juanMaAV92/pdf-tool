from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.images2pdf.params import ImagesToPdfParams

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _noop(_p: float, _m: str) -> None:
    pass


def output_path_for_images(input_path: Path) -> Path:
    """`<imagen>.pdf` junto al original, sin pisar un archivo existente."""
    p = Path(input_path)
    candidate = p.parent / f"{p.stem}.pdf"
    n = 1
    while candidate.exists():
        candidate = p.parent / f"{p.stem}_{n}.pdf"
        n += 1
    return candidate


def _convert_one(input_path: Path, progress: Progress) -> tuple[Path | None, str]:
    """Convierte una imagen. Devuelve (salida, etiqueta) o (None, error corto)."""
    try:
        if input_path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("Formato no soportado (usa JPG o PNG).")
        progress(0.0, "Convirtiendo imagen…")
        out = output_path_for_images(input_path)
        # convert_to_pdf genera una página del tamaño exacto de la imagen.
        with fitz.open(str(input_path)) as img:
            pdf_bytes = img.convert_to_pdf()
        with fitz.open("pdf", pdf_bytes) as pdf:
            pdf.save(str(out), garbage=4, deflate=True)
        progress(1.0, "Listo")
        return out, f"→ {out.name}"
    except Exception as exc:  # esta imagen falla; el lote continúa
        return None, str(exc)


def images_to_pdf(inputs: list[Path], params: ImagesToPdfParams,
                  progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    paths = [Path(p) for p in inputs]
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)

    total = len(paths)
    outputs: list[Path] = []
    labels: list[str] = []

    for index, path in enumerate(paths):
        def scoped(pct: float, msg: str, _i: int = index,
                   _name: str = path.name) -> None:
            overall = (_i + pct) / total
            label = f"[{_i + 1}/{total}] {_name}: {msg}" if total > 1 else msg
            progress(overall, label)

        out, label = _convert_one(path, scoped)
        if out is not None:
            outputs.append(out)
        labels.append(label)

    if not outputs:
        raise ValueError(labels[0] if total == 1
                         else "Ninguna imagen pudo convertirse.")

    if total == 1:
        return ToolResult(outputs=outputs,
                          summary=f"Imagen convertida → {outputs[0].name}")

    progress(1.0, "Listo")
    if len(outputs) == total:
        summary = f"{total} imágenes convertidas"
    else:
        summary = f"{len(outputs)} de {total} imágenes convertidas"
    return ToolResult(outputs=outputs, summary=summary, details=labels)
