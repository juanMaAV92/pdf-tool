from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import pymupdf

from pdftool.core.atomic import atomic_output_dir
from pdftool.core.batch import Outcome, noop_progress, run_batch
from pdftool.core.errors import UserError
from pdftool.core.naming import localized_suffix, output_dir_path, series_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.i18n import t
from pdftool.tools.pdf2images.params import Pdf2ImagesParams

# A0 a 300 ppp son 139,5 MP y unos 418 MB de memoria: cabe. Más arriba, una sola
# página podría agotar la memoria del equipo.
MAX_PIXELS = 150_000_000
# El formato JPEG no admite más: fuera de ahí el error de la librería es opaco.
MAX_JPG_SIDE = 65_500
JPG_QUALITY = 90
_MIN_DPI = Pdf2ImagesParams.model_fields["dpi"].metadata[0].ge
_MAX_DPI = Pdf2ImagesParams.model_fields["dpi"].metadata[1].le
_MIN_NUMBER_WIDTH = 3


def page_pixels(rect: pymupdf.Rect, dpi: int) -> tuple[int, int]:
    """Tamaño exacto de la imagen de una página: el mismo que se renderiza.

    Un `round()` del tamaño en puntos no coincide con el render; esta es la
    única fuente de los píxeles que se muestran y se exportan.
    """
    zoom = dpi / 72
    box = (rect * pymupdf.Matrix(zoom, zoom)).irect
    return box.width, box.height


def _fits(rect: pymupdf.Rect, dpi: int, image_format: str) -> bool:
    width, height = page_pixels(rect, dpi)
    if width * height > MAX_PIXELS:
        return False
    return image_format != "jpg" or max(width, height) <= MAX_JPG_SIDE


def _max_dpi(rect: pymupdf.Rect, image_format: str) -> int | None:
    """Mayor resolución permitida que cabe, o None si no cabe ninguna."""
    if not _fits(rect, _MIN_DPI, image_format):
        return None
    low, high = _MIN_DPI, _MAX_DPI
    while low < high:
        middle = (low + high + 1) // 2
        if _fits(rect, middle, image_format):
            low = middle
        else:
            high = middle - 1
    return low


def check_limits(doc: pymupdf.Document, dpi: int, image_format: str) -> None:
    """Rechaza el PDF antes de renderizar si alguna página no cabe."""
    for index in range(doc.page_count):
        rect = doc[index].rect
        if _fits(rect, dpi, image_format):
            continue
        number = index + 1
        max_dpi = _max_dpi(rect, image_format)
        if max_dpi is None:
            raise UserError(t("tool.pdf2images.error.too_large_any", page=number))
        raise UserError(
            t("tool.pdf2images.error.too_large", page=number, dpi=dpi, max_dpi=max_dpi)
        )


def first_page_rect(path: Path) -> pymupdf.Rect:
    """Tamaño de la primera página, para anticipar los píxeles en el panel."""
    with pymupdf.open(path) as doc:
        return doc[0].rect


def result_folder_for(folders: Sequence[Path]) -> Path:
    """La carpeta que reúne el resultado de un lote.

    Si solo tienen la raíz en común, o están en unidades distintas, abrir la
    raíz no ayudaría: se usa la primera.
    """
    if len(folders) == 1:
        return folders[0]
    try:
        common = Path(os.path.commonpath(folders))
    except ValueError:
        return folders[0]
    return folders[0] if common.parent == common else common


def _export_one(
    path: Path, params: Pdf2ImagesParams, progress: Progress, images: list[Path]
) -> Outcome:
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise UserError(t("core.pages.error.password", tool=t("tool.protect.name")))
        check_limits(doc, params.dpi, params.format)
        warnings: tuple[str, ...] = ()
        if doc.metadata and doc.metadata.get("encryption"):
            warnings = (t("tool.pdf2images.warning.restricted"),)

        total = doc.page_count
        width = max(_MIN_NUMBER_WIDTH, len(str(total)))
        zoom = params.dpi / 72
        matrix = pymupdf.Matrix(zoom, zoom)
        target = output_dir_path(
            path, localized_suffix("tool.pdf2images.suffix"), out_dir=params.output_dir
        )
        names: list[str] = []
        with atomic_output_dir(target) as temporary:
            for index, page in enumerate(doc):
                # `progress` lanza JobCancelled: se cancela entre páginas.
                progress(
                    index / total,
                    t("tool.pdf2images.progress.page", page=index + 1, count=total),
                )
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                pixmap.set_dpi(params.dpi, params.dpi)
                if params.format == "jpg":
                    data = pixmap.tobytes("jpeg", jpg_quality=JPG_QUALITY)
                else:
                    data = pixmap.tobytes("png")
                # Desde Python y no con Pixmap.save: las rutas no ASCII de
                # Windows quedan a cargo del sistema de archivos de Python.
                image = series_path(
                    temporary, path.stem, index + 1, width, params.format
                )
                image.write_bytes(data)
                names.append(image.name)

    images.extend(target / name for name in names)
    return Outcome(
        output=target,
        message=t("tool.pdf2images.item", count=total),
        warnings=warnings,
        metrics={"pages": total},
    )


def pdf2images(
    inputs: list[Path], params: Pdf2ImagesParams, progress: Progress = noop_progress
) -> ToolResult:
    images: list[Path] = []
    batch = run_batch(
        inputs,
        lambda path, scoped: _export_one(path, params, scoped, images),
        progress,
        all_failed=t("tool.pdf2images.error.all_failed"),
    )
    progress(1.0, t("common.progress.done"))
    folder = result_folder_for(batch.outputs)
    failed = batch.total - len(batch.outputs)
    if failed:
        summary = t(
            "tool.pdf2images.summary.partial",
            count=len(images),
            folder=folder.name,
            failed=failed,
        )
    else:
        summary = t("tool.pdf2images.summary", count=len(images), folder=folder.name)
    return ToolResult(
        outputs=images,
        summary=summary,
        items=batch.items,
        metrics={"images": len(images)},
    )
