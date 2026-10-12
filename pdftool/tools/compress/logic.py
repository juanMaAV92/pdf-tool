from __future__ import annotations

import re
from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_copy, atomic_output
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.naming import output_path
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

_PRESERVE_ATTEMPTS = [
    {"dpi_threshold": 150, "dpi_target": 120, "quality": 75},
    {"dpi_threshold": 120, "dpi_target": 96, "quality": 60},
    {"dpi_threshold": 96, "dpi_target": 72, "quality": 45},
]


def _size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def _target_label(target_mb: float) -> str:
    if target_mb.is_integer():
        return f"{int(target_mb)}MB"
    return f"{target_mb:g}MB".replace(".", "_")


# También absorbe un « (n)» final (ver _clean_stem). Esto puede recortar de
# más un nombre de usuario legítimo que combine un token «_NMB» con un « (n)»
# final (p. ej. «presupuesto_2MB (1).pdf» -> «presupuesto»), pero nunca causa
# pérdida de archivos: `output_path` pasa `taken=(p,)`, así que el nombre
# limpio jamás puede resolver de vuelta a la propia entrada. Como mucho el
# resultado es un nombre cosméticamente raro.
_STEM_NOISE = re.compile(r"(_compressed|_\d+(?:_\d+)?MB)+( \(\d+\))?$")


def _clean_stem(stem: str) -> str:
    """Quita sufijos de compresiones previas para que no se acumulen.

    Absorbe también un « (n)» final, para que recomprimir una salida ya
    desambiguada no produzca «doc_5MB (1)_2MB.pdf».
    """
    return _STEM_NOISE.sub("", stem)


def output_path_for(
    input_path: Path, target_mb: float, out_dir: Path | None = None
) -> Path:
    """Política de nombre de Comprimir; la colisión la resuelve el helper."""
    p = Path(input_path)
    return output_path(
        p, _target_label(target_mb), stem=_clean_stem(p.stem), out_dir=out_dir
    )


def _simple_compress(src: Path, dst: Path) -> None:
    with atomic_output(dst) as temporary:
        with fitz.open(src) as doc:
            doc.save(str(temporary), garbage=4, deflate=True, clean=True)


def _rerender(src: Path, dst: Path, *, max_dimension: int, jpg_quality: int) -> None:
    with atomic_output(dst) as temporary:
        with fitz.open(src) as source, fitz.open() as doc:
            for page_num in range(len(source)):
                src_page = source[page_num]
                rect = src_page.rect
                if rect.width == 0 or rect.height == 0:
                    continue
                # Sin zoom mínimo: el lado mayor nunca pasa de `max_dimension`,
                # así una página enorme no se convierte en decenas de MP.
                zoom = min(max_dimension / rect.width, max_dimension / rect.height, 2.0)
                pix = src_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img_bytes = pix.tobytes("jpg", jpg_quality=jpg_quality)
                new_page = doc.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(new_page.rect, stream=img_bytes)
            doc.save(str(temporary), garbage=4, deflate=True)


def _preserve_compress(
    src: Path, dst: Path, *, dpi_threshold: int, dpi_target: int, quality: int
) -> None:
    """Optimiza imágenes sin convertir las páginas completas en imágenes."""
    with atomic_output(dst) as temporary:
        with fitz.open(src) as doc:
            rewrite_images = getattr(doc, "rewrite_images", None)
            if rewrite_images is not None:
                rewrite_images(
                    dpi_threshold=dpi_threshold,
                    dpi_target=dpi_target,
                    quality=quality,
                )
            doc.save(
                str(temporary),
                garbage=4,
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                clean=True,
            )


def _compress_one(
    input_path: Path,
    out: Path,
    target_mb: float,
    progress: Progress,
    mode: str = "max",
) -> tuple[Path, str, float, float]:
    original = _size_mb(input_path)
    progress(0.0, f"Tamaño original: {original:.2f} MB")

    if original <= target_mb:
        atomic_copy(input_path, out)
        progress(1.0, "Ya está bajo el objetivo")
        return out, f"{original:.2f} MB (sin cambios)", original, original

    _simple_compress(input_path, out)
    current = _size_mb(out)
    progress(0.1, f"Compresión simple: {current:.2f} MB")
    if current <= target_mb:
        progress(1.0, "Listo (compresión simple)")
        return out, f"{original:.2f} MB → {current:.2f} MB", original, current

    if mode == "preserve":
        for i, attempt in enumerate(_PRESERVE_ATTEMPTS):
            progress(
                (i + 1) / (len(_PRESERVE_ATTEMPTS) + 1),
                f"Optimización de imágenes {i + 1}: "
                f"{attempt['dpi_target']} dpi, {attempt['quality']}%",
            )
            _preserve_compress(input_path, out, **attempt)
            current = _size_mb(out)
            if current <= target_mb:
                progress(1.0, f"Listo: {current:.2f} MB (contenido preservado)")
                return (
                    out,
                    f"{original:.2f} MB → {current:.2f} MB (contenido preservado)",
                    original,
                    current,
                )

        progress(1.0, f"Mejor esfuerzo: {current:.2f} MB (contenido preservado)")
        return (
            out,
            f"{original:.2f} MB → {current:.2f} MB "
            "(no se alcanzó el objetivo; contenido preservado)",
            original,
            current,
        )

    n = len(_ATTEMPTS)
    for i, attempt in enumerate(_ATTEMPTS):
        progress(
            (i + 1) / (n + 1),
            f"Intento {i + 1}: {attempt['max_dimension']}px, {attempt['jpg_quality']}%",
        )
        _rerender(input_path, out, **attempt)
        current = _size_mb(out)
        if current <= target_mb:
            progress(1.0, f"Listo: {current:.2f} MB")
            return out, f"{original:.2f} MB → {current:.2f} MB", original, current

    progress(1.0, f"Mejor esfuerzo: {current:.2f} MB")
    return (
        out,
        f"{original:.2f} MB → {current:.2f} MB (no se alcanzó el objetivo)",
        original,
        current,
    )


def compress(
    inputs: list[Path], params: CompressParams, progress: Progress = noop_progress
) -> ToolResult:
    target_mb = params.target_mb
    sizes: list[tuple[float, float]] = []

    def one(path: Path, scoped: Progress) -> tuple[Path, str]:
        out = output_path_for(path, target_mb, params.output_dir)
        try:
            _, summary, original, final = _compress_one(
                path, out, target_mb, scoped, params.mode
            )
        except BaseException:
            # Los intentos van publicando salidas intermedias; si el archivo
            # falla o se cancela, no se deja un resultado a medias. `out` lo
            # eligió `output_path`, así que no existía antes de este archivo.
            out.unlink(missing_ok=True)
            raise
        sizes.append((original, final))
        return out, summary

    batch = run_batch(inputs, one, progress, all_failed="Ningún PDF pudo comprimirse.")
    outputs, total = batch.outputs, batch.total

    if total == 1:
        return ToolResult(outputs=outputs, summary=batch.items[0].message)

    total_original = sum(original for original, _ in sizes)
    total_final = sum(final for _, final in sizes)
    saved = total_original - total_final
    pct = (saved / total_original * 100) if total_original else 0.0
    tail = f" ({pct:.0f}% menos)" if saved > 0.005 else " (sin cambios)"
    progress(1.0, f"{len(outputs)} archivos comprimidos")
    head = (
        f"{total} archivos"
        if len(outputs) == total
        else f"{len(outputs)} de {total} archivos"
    )
    return ToolResult(
        outputs=outputs,
        summary=f"{head} · {total_original:.2f} MB → {total_final:.2f} MB{tail}",
        items=batch.items,
    )
