from __future__ import annotations

import re
import shutil
from pathlib import Path

import fitz

from pdftool.core.plugin import Progress, ToolResult
from pdftool.tools.compress.params import CompressParams

_ATTEMPTS = [
    {"max_dimension": 2000, "jpg_quality": 85},
    {"max_dimension": 1800, "jpg_quality": 75},
    {"max_dimension": 1500, "jpg_quality": 65},
    {"max_dimension": 1200, "jpg_quality": 55},
    {"max_dimension": 1000, "jpg_quality": 45},
    {"max_dimension": 800, "jpg_quality": 35},
    {"max_dimension": 600, "jpg_quality": 25},
]


def _noop(_p: float, _m: str) -> None:
    pass


def _size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def _target_label(target_mb: float) -> str:
    if target_mb.is_integer():
        return f"{int(target_mb)}MB"
    return f"{target_mb:g}MB".replace(".", "_")


def output_path_for(input_path: Path, target_mb: float) -> Path:
    stem = re.sub(r"(_compressed|_\d+(?:_\d+)?MB)+$", "", input_path.stem)
    return input_path.parent / f"{stem}_{_target_label(target_mb)}.pdf"


def _simple_compress(src: Path, dst: Path) -> None:
    with fitz.open(src) as doc:
        doc.save(str(dst), garbage=4, deflate=True, clean=True)


def _rerender(src: Path, dst: Path, *, max_dimension: int, jpg_quality: int) -> None:
    with fitz.open(src) as source, fitz.open() as doc:
        for page_num in range(len(source)):
            src_page = source[page_num]
            rect = src_page.rect
            if rect.width == 0 or rect.height == 0:
                continue
            zoom = min(max_dimension / rect.width, max_dimension / rect.height, 2.0)
            zoom = max(zoom, 0.5)
            pix = src_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img_bytes = pix.tobytes("jpg", jpg_quality=jpg_quality)
            new_page = doc.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(new_page.rect, stream=img_bytes)
        doc.save(str(dst), garbage=4, deflate=True)


def compress(inputs: list[Path], params: CompressParams,
             progress: Progress = _noop) -> ToolResult:
    if not inputs:
        raise ValueError("inputs está vacío")
    input_path = Path(inputs[0])
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    target_mb = params.target_mb
    out = output_path_for(input_path, target_mb)
    original = _size_mb(input_path)
    progress(0.0, f"Tamaño original: {original:.2f} MB")

    if original <= target_mb:
        shutil.copy2(input_path, out)
        progress(1.0, "Ya está bajo el objetivo")
        return ToolResult(outputs=[out], summary=f"{original:.2f} MB (sin cambios)")

    _simple_compress(input_path, out)
    current = _size_mb(out)
    progress(0.1, f"Compresión simple: {current:.2f} MB")
    if current <= target_mb:
        progress(1.0, "Listo (compresión simple)")
        return ToolResult(outputs=[out], summary=f"{original:.2f} MB → {current:.2f} MB")

    n = len(_ATTEMPTS)
    for i, attempt in enumerate(_ATTEMPTS):
        progress((i + 1) / (n + 1),
                 f"Intento {i + 1}: {attempt['max_dimension']}px, {attempt['jpg_quality']}%")
        _rerender(input_path, out, **attempt)
        current = _size_mb(out)
        if current <= target_mb:
            progress(1.0, f"Listo: {current:.2f} MB")
            return ToolResult(outputs=[out], summary=f"{original:.2f} MB → {current:.2f} MB")

    progress(1.0, f"Mejor esfuerzo: {current:.2f} MB")
    return ToolResult(
        outputs=[out],
        summary=f"{original:.2f} MB → {current:.2f} MB (no se alcanzó el objetivo)",
    )
