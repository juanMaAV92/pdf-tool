from __future__ import annotations

import re
import tempfile
from collections.abc import Callable
from functools import partial
from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_copy
from pdftool.core.batch import noop_progress, run_batch
from pdftool.core.jobs import JobCancelled
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
    with fitz.open(src) as doc:
        doc.save(str(dst), garbage=4, deflate=True, clean=True)


def _rerender(
    src: Path,
    dst: Path,
    *,
    max_dimension: int,
    jpg_quality: int,
    progress: Progress = noop_progress,
) -> None:
    with fitz.open(src) as source, fitz.open() as doc:
        total = len(source)
        for page_num in range(total):
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
            # Un punto de progreso (y de cancelación) por página: un intento
            # sobre un PDF largo puede durar decenas de segundos.
            progress((page_num + 1) / total, f"página {page_num + 1} de {total}")
        doc.save(str(dst), garbage=4, deflate=True)


def _preserve_compress(
    src: Path, dst: Path, *, dpi_threshold: int, dpi_target: int, quality: int
) -> None:
    """Optimiza imágenes sin convertir las páginas completas en imágenes."""
    with fitz.open(src) as doc:
        rewrite_images = getattr(doc, "rewrite_images", None)
        if rewrite_images is not None:
            rewrite_images(
                dpi_threshold=dpi_threshold,
                dpi_target=dpi_target,
                quality=quality,
            )
        doc.save(
            str(dst),
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )


class _Candidates:
    """Conserva solo el intento más pequeño dentro de una carpeta temporal.

    Los intentos no tocan la carpeta del usuario: solo el ganador se publica,
    una vez, al final.
    """

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        self._count = 0
        self.best: Path | None = None
        self.best_mb = float("inf")

    def attempt(self, make: Callable[[Path], None]) -> float:
        self._count += 1
        candidate = self._workdir / f"intento-{self._count}.pdf"
        make(candidate)
        size = _size_mb(candidate)
        if size < self.best_mb:
            if self.best is not None:
                self.best.unlink(missing_ok=True)
            self.best, self.best_mb = candidate, size
        else:
            candidate.unlink(missing_ok=True)
        return size


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

    with tempfile.TemporaryDirectory(prefix="pdf-tool-") as workdir:
        candidates = _Candidates(Path(workdir))

        def publish(note: str = "") -> tuple[Path, str, float, float]:
            assert candidates.best is not None
            atomic_copy(candidates.best, out)
            final = candidates.best_mb
            progress(1.0, f"Listo: {final:.2f} MB")
            return out, f"{original:.2f} MB → {final:.2f} MB{note}", original, final

        progress(0.05, "Optimizando la estructura del PDF…")
        if (
            candidates.attempt(lambda dst: _simple_compress(input_path, dst))
            <= target_mb
        ):
            return publish()

        if mode == "preserve":
            n = len(_PRESERVE_ATTEMPTS)
            for i, attempt in enumerate(_PRESERVE_ATTEMPTS):
                progress(
                    0.1 + 0.9 * i / n, f"Reduciendo imágenes (paso {i + 1} de {n})…"
                )
                size = candidates.attempt(
                    partial(
                        _preserve_compress,
                        input_path,
                        dpi_threshold=attempt["dpi_threshold"],
                        dpi_target=attempt["dpi_target"],
                        quality=attempt["quality"],
                    )
                )
                if size <= target_mb:
                    return publish(" (contenido preservado)")
            return publish(
                " (no se alcanzó el objetivo; se guardó la versión más pequeña "
                "con el contenido preservado)"
            )

        n = len(_ATTEMPTS)
        for i, attempt in enumerate(_ATTEMPTS):
            base = 0.1 + 0.9 * i / n
            step = f"Reduciendo calidad (paso {i + 1} de {n})"
            progress(base, f"{step}…")

            def step_progress(
                pct: float, msg: str, _base: float = base, _step: str = step
            ) -> None:
                progress(_base + 0.9 / n * pct, f"{_step}: {msg}")

            size = candidates.attempt(
                partial(
                    _rerender,
                    input_path,
                    max_dimension=attempt["max_dimension"],
                    jpg_quality=attempt["jpg_quality"],
                    progress=step_progress,
                )
            )
            if size <= target_mb:
                return publish()
        return publish(
            " (no se alcanzó el objetivo; se guardó la versión más pequeña posible)"
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
        except JobCancelled:
            # Cancelar conserva lo ya terminado, como en el resto de
            # herramientas («Los archivos ya terminados se conservan»).
            raise
        except Exception:
            # Un fallo tras publicar no debe dejar un resultado que la UI no
            # va a reportar. `out` lo eligió `output_path`, así que no existía
            # antes de este archivo.
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
