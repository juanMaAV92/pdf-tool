from __future__ import annotations

import math
from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_output
from pdftool.core.batch import noop_progress
from pdftool.core.naming import output_path
from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.watermark.params import WatermarkParams

_ANGLE = 45
# Tope de sellos por página: el mosaico crece con el área de la página y el
# coste de insert_text crece de forma cuadrática con los sellos de una misma
# página (2000 ≈ 5 s; 4000 ≈ 22 s). Con este tope A4, Letter y A3 no cambian ni
# a 8 pt; solo páginas mayores con letra pequeña ganan separación.
_MAX_STAMPS_PER_PAGE = 2_000


def output_path_for_watermark(input_path: Path, out_dir: Path | None = None) -> Path:
    """Política de nombre de Marca de agua; la colisión la resuelve el helper."""
    return output_path(input_path, "marca", out_dir=out_dir)


def _stamp_count(rect: fitz.Rect, sx: float, sy: float, text_w: float) -> int:
    """Sellos que pondrá el mosaico (mismos límites que el bucle de `watermark`)."""
    cols = math.ceil((rect.width + sx + text_w) / sx)
    rows = math.ceil((rect.height + sy / 2) / sy)
    return cols * rows


def _grid_steps(
    rect: fitz.Rect, step_x: float, step_y: float, text_w: float
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
    rot = fitz.Matrix(_ANGLE)
    text_w = fitz.get_text_length(text, fontsize=params.font_size)
    # Separación de la rejilla (mosaico): ancho del texto + holgura.
    step_x = max(text_w + params.font_size * 2, params.font_size * 4)
    step_y = params.font_size * 4

    progress(0.0, "Aplicando marca de agua…")
    with atomic_output(out) as temporary:
        with fitz.open(str(input_path)) as doc:
            total = doc.page_count
            for pno in range(total):
                page = doc[pno]
                rect = page.rect
                sx, sy = _grid_steps(rect, step_x, step_y, text_w)
                y = sy / 2
                while y < rect.height + sy:
                    x = -text_w
                    while x < rect.width + sx:
                        pivot = fitz.Point(x, y)
                        page.insert_text(
                            pivot,
                            text,
                            fontsize=params.font_size,
                            color=tuple(params.color),
                            fill_opacity=params.opacity,
                            morph=(pivot, rot),
                            overlay=True,
                        )
                        x += sx
                    y += sy
                progress((pno + 1) / total, f"Página {pno + 1}/{total}")
            doc.save(str(temporary), garbage=4, deflate=True)

    progress(1.0, f"Listo: {out.name}")
    return ToolResult(outputs=[out], summary=f"Marca '{text}' aplicada → {out.name}")
