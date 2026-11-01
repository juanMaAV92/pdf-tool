from __future__ import annotations

import math
from pathlib import Path

import pymupdf

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress
from pdftool.core.naming import output_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.i18n import t
from pdftool.tools.watermark.params import WatermarkParams

_ANGLE = 45
# Tope de sellos por página: el mosaico crece con el área de la página. Queda por
# encima de un A0 con letra de 8 pt (~8000), así que solo actúa ante páginas
# fuera de lo normal (hasta 14400 pt de lado).
_MAX_STAMPS_PER_PAGE = 20_000


def output_path_for_watermark(input_path: Path, out_dir: Path | None = None) -> Path:
    """Política de nombre de Marca de agua; la colisión la resuelve el helper."""
    return output_path(input_path, t("tool.watermark.suffix"), out_dir=out_dir)


def _stamp_count(rect: pymupdf.Rect, sx: float, sy: float, text_w: float) -> int:
    """Sellos que pondrá el mosaico (mismos límites que el bucle de `watermark`)."""
    cols = math.ceil((rect.width + sx + text_w) / sx)
    rows = math.ceil((rect.height + sy / 2) / sy)
    return cols * rows


def _grid_steps(
    rect: pymupdf.Rect, step_x: float, step_y: float, text_w: float
) -> tuple[float, float]:
    """Separación del mosaico, ampliada si la página pediría demasiados sellos."""
    stamps = _stamp_count(rect, step_x, step_y, text_w)
    if stamps <= _MAX_STAMPS_PER_PAGE:
        return step_x, step_y
    scale = math.sqrt(stamps / _MAX_STAMPS_PER_PAGE)
    while _stamp_count(rect, step_x * scale, step_y * scale, text_w) > (
        _MAX_STAMPS_PER_PAGE
    ):
        scale *= 1.05
    return step_x * scale, step_y * scale


def _tile_page(
    page: pymupdf.Page,
    text: str,
    params: WatermarkParams,
    font: pymupdf.Font,
    step_x: float,
    step_y: float,
    text_w: float,
) -> None:
    """Cubre la página con el texto girado `_ANGLE` grados en mosaico.

    Cada sello gira sobre su propio punto de inicio. En vez de un insert_text
    por sello (coste cuadrático: cada llamada reescribe el contenido de la
    página), todos van en un único TextWriter con una sola rotación alrededor
    del centro: cada sello se coloca en el punto que esa rotación lleva a su
    posición final, con idéntico resultado.
    """
    rect = page.rect
    sx, sy = _grid_steps(rect, step_x, step_y, text_w)
    center = pymupdf.Point(rect.width / 2, rect.height / 2)
    # `morph` gira en el sistema de PDF (y hacia arriba); en coordenadas de
    # página la rotación inversa equivale a la misma matriz.
    rot = pymupdf.Matrix(_ANGLE)
    writer = pymupdf.TextWriter(rect, opacity=params.opacity, color=tuple(params.color))
    y = sy / 2
    while y < rect.height + sy:
        x = -text_w
        while x < rect.width + sx:
            start = (pymupdf.Point(x, y) - center) * rot + center
            writer.append(start, text, font=font, fontsize=params.font_size)
            x += sx
        y += sy
    writer.write_text(page, morph=(center, rot), overlay=True)


def watermark(
    inputs: list[Path], params: WatermarkParams, progress: Progress = noop_progress
) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    input_path = Path(inputs[0])
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    out = output_path_for_watermark(input_path, params.output_dir)
    text = params.text
    text_w = pymupdf.get_text_length(text, fontsize=params.font_size)
    # Separación de la rejilla (mosaico): ancho del texto + holgura.
    step_x = max(text_w + params.font_size * 2, params.font_size * 4)
    step_y = params.font_size * 4

    progress(0.0, t("tool.watermark.progress.start"))
    font = pymupdf.Font("helv")
    with atomic_output(out) as temporary, pymupdf.open(str(input_path)) as doc:
        total = doc.page_count
        for pno in range(total):
            page = doc[pno]
            _tile_page(page, text, params, font, step_x, step_y, text_w)
            progress(
                (pno + 1) / total,
                t("tool.watermark.progress.page", page=pno + 1, total=total),
            )
        doc.save(str(temporary), garbage=4, deflate=True)

    progress(1.0, t("common.progress.done_file", name=out.name))
    return ToolResult(
        outputs=[out],
        summary=t("tool.watermark.summary", text=text, name=out.name),
    )
