from __future__ import annotations

from pathlib import Path

import pymupdf

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.errors import UserError
from pdftool.core.naming import unique_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.i18n import t
from pdftool.tools.images2pdf.params import ImagesToPdfParams

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png"}
# Una imagen de pocos KB puede declarar 60000×60000 px y agotar la memoria al
# decodificarla; se rechaza leyendo solo la cabecera.
MAX_IMAGE_PIXELS = 120_000_000

# Marcadores JPEG SOFn con dimensiones (excluye DHT, JPG y DAC).
_JPEG_SOF = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def image_size(path: Path) -> tuple[int, int] | None:
    """(ancho, alto) leídos de la cabecera PNG/JPEG, sin decodificar. None si
    no se reconoce."""
    with open(path, "rb") as f:
        head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            return int.from_bytes(head[16:20], "big"), int.from_bytes(
                head[20:24], "big"
            )
        if head[:2] != b"\xff\xd8":
            return None
        f.seek(2)
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                return None
            if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
                continue
            length_bytes = f.read(2)
            if len(length_bytes) < 2:
                return None
            length = int.from_bytes(length_bytes, "big")
            if marker[1] in _JPEG_SOF:
                data = f.read(5)
                if len(data) < 5:
                    return None
                return int.from_bytes(data[3:5], "big"), int.from_bytes(
                    data[1:3], "big"
                )
            f.seek(length - 2, 1)


def _check_pixels(path: Path) -> None:
    size = image_size(path)
    if size is None:
        return  # formato no reconocido: lo decidirá MuPDF
    width, height = size
    if width * height > MAX_IMAGE_PIXELS:
        raise UserError(t("tool.images2pdf.error.too_big", width=width, height=height))


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
        raise UserError(t("tool.images2pdf.error.format"))
    _check_pixels(input_path)
    progress(0.0, t("tool.images2pdf.progress.converting"))
    out = output_path_for_images(input_path, out_dir)
    # convert_to_pdf genera una página del tamaño exacto de la imagen.
    with pymupdf.open(str(input_path)) as img:
        pdf_bytes = img.convert_to_pdf()
    with atomic_output(out) as temporary, pymupdf.open("pdf", pdf_bytes) as pdf:
        pdf.save(str(temporary), garbage=4, deflate=True)
    progress(1.0, t("common.progress.done"))
    return out, t("common.item.output", name=out.name)


def images_to_pdf(
    inputs: list[Path], params: ImagesToPdfParams, progress: Progress = noop_progress
) -> ToolResult:
    batch = run_batch(
        inputs,
        lambda path, scoped: _convert_one(path, scoped, params.output_dir),
        progress,
        all_failed=t("tool.images2pdf.all_failed"),
    )
    outputs, total = batch.outputs, batch.total

    if total == 1:
        return ToolResult(
            outputs=outputs,
            summary=t("tool.images2pdf.summary.one", name=outputs[0].name),
        )

    progress(1.0, t("common.progress.done"))
    if len(outputs) == total:
        summary = t("tool.images2pdf.summary.all", count=total)
    else:
        summary = t("tool.images2pdf.summary.partial", done=len(outputs), count=total)
    return ToolResult(outputs=outputs, summary=summary, items=batch.items)
