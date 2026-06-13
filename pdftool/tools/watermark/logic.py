from __future__ import annotations

from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.watermark.params import WatermarkParams

_ANGLE = 45


def _noop(_p: float, _m: str) -> None:
    pass


def output_path_for_watermark(input_path: Path) -> Path:
    p = Path(input_path)
    candidate = p.parent / f"{p.stem}_marca.pdf"
    if candidate == p:  # por si el original ya se llamara así
        candidate = p.parent / f"{p.stem}_marca_1.pdf"
    return candidate


def watermark(inputs: list[Path], params: WatermarkParams,
              progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    input_path = Path(inputs[0])
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    out = output_path_for_watermark(input_path)
    text = params.text
    rot = fitz.Matrix(_ANGLE)
    text_w = fitz.get_text_length(text, fontsize=params.font_size)
    # Separación de la rejilla (mosaico): ancho del texto + holgura.
    step_x = max(text_w + params.font_size * 2, params.font_size * 4)
    step_y = params.font_size * 4

    progress(0.0, "Aplicando marca de agua…")
    with fitz.open(str(input_path)) as doc:
        total = doc.page_count
        for pno in range(total):
            page = doc[pno]
            rect = page.rect
            y = step_y / 2
            while y < rect.height + step_y:
                x = -text_w
                while x < rect.width + step_x:
                    pivot = fitz.Point(x, y)
                    page.insert_text(
                        pivot, text,
                        fontsize=params.font_size,
                        color=tuple(params.color),
                        fill_opacity=params.opacity,
                        morph=(pivot, rot),
                        overlay=True,
                    )
                    x += step_x
                y += step_y
            progress((pno + 1) / total, f"Página {pno + 1}/{total}")
        doc.save(str(out), garbage=4, deflate=True)

    progress(1.0, f"Listo: {out.name}")
    return ToolResult(outputs=[out], summary=f"Marca '{text}' aplicada → {out.name}")
