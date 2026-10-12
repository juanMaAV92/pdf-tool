from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import fitz

from pdftool.core.atomic import atomic_copy
from pdftool.core.batch import Outcome, noop_progress, run_batch
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


# Páginas que se acumulan en memoria antes de volcar el PDF de salida a disco.
# Sin este volcado, el documento entero (todas sus imágenes JPEG) vive en RAM
# hasta el final: ~0,3 MB por página en un A4.
_RERENDER_CHUNK = 50


def _rerender(
    src: Path,
    dst: Path,
    *,
    max_dimension: int,
    jpg_quality: int,
    progress: Progress = noop_progress,
) -> None:
    with fitz.open(src) as source:
        total = len(source)
        doc = fitz.open()
        flushed = False
        try:
            for page_num in range(total):
                src_page = source[page_num]
                rect = src_page.rect
                if rect.width > 0 and rect.height > 0:
                    # Sin zoom mínimo: el lado mayor nunca pasa de `max_dimension`,
                    # así una página enorme no se convierte en decenas de MP.
                    zoom = min(
                        max_dimension / rect.width, max_dimension / rect.height, 2.0
                    )
                    pix = src_page.get_pixmap(
                        matrix=fitz.Matrix(zoom, zoom), alpha=False
                    )
                    img_bytes = pix.tobytes("jpg", jpg_quality=jpg_quality)
                    new_page = doc.new_page(width=rect.width, height=rect.height)
                    new_page.insert_image(new_page.rect, stream=img_bytes)
                done = page_num + 1
                if done % _RERENDER_CHUNK == 0 and done < total:
                    # Volcar a disco y reabrir libera las imágenes ya escritas.
                    if flushed:
                        doc.saveIncr()
                    else:
                        doc.save(str(dst))
                        flushed = True
                    doc.close()
                    doc = fitz.open(str(dst))
                # Un punto de progreso (y de cancelación) por página: un intento
                # sobre un PDF largo puede durar decenas de segundos.
                progress(done / total, f"página {done} de {total}")
            if not flushed:
                doc.save(str(dst), garbage=4, deflate=True)
                return
            doc.saveIncr()
        finally:
            doc.close()
    # Los volcados incrementales dejan versiones intermedias: se compacta.
    compact = dst.with_name(f".{dst.name}.compact")
    try:
        with fitz.open(str(dst)) as doc:
            doc.save(str(compact), garbage=4, deflate=True)
        os.replace(compact, dst)
    finally:
        compact.unlink(missing_ok=True)


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
        # Si el ganador convirtió páginas en imagen (pierden texto y enlaces).
        self.best_rasterized = False

    def attempt(
        self, make: Callable[[Path], None], *, rasterizes: bool = False
    ) -> float:
        self._count += 1
        candidate = self._workdir / f"intento-{self._count}.pdf"
        make(candidate)
        size = _size_mb(candidate)
        if size < self.best_mb:
            if self.best is not None:
                self.best.unlink(missing_ok=True)
            self.best, self.best_mb = candidate, size
            self.best_rasterized = rasterizes
        else:
            candidate.unlink(missing_ok=True)
        return size


RASTERIZED_WARNING = (
    "Algunas páginas se convirtieron en imagen: puede haberse perdido texto "
    "seleccionable, enlaces o anotaciones. Si los necesitas, usa «Conservar "
    "texto y enlaces»."
)


@dataclass(frozen=True)
class _Compressed:
    message: str
    original_mb: float
    final_mb: float
    rasterized: bool

    @property
    def saved_pct(self) -> float:
        if self.original_mb <= 0:
            return 0.0
        return max(0.0, (self.original_mb - self.final_mb) / self.original_mb * 100)

    def outcome(self, out: Path) -> Outcome:
        return Outcome(
            out,
            self.message,
            warnings=(RASTERIZED_WARNING,) if self.rasterized else (),
            metrics={
                "original_mb": self.original_mb,
                "final_mb": self.final_mb,
                "saved_pct": self.saved_pct,
            },
        )


def _saved_label(original: float, final: float) -> str:
    saved = (original - final) / original * 100 if original > 0 else 0.0
    return f" · {saved:.0f} % menos" if saved >= 0.5 else ""


def _compress_one(
    input_path: Path,
    out: Path,
    target_mb: float,
    progress: Progress,
    mode: str = "max",
) -> _Compressed:
    original = _size_mb(input_path)
    progress(0.0, f"Tamaño original: {original:.2f} MB")

    if original <= target_mb:
        atomic_copy(input_path, out)
        progress(1.0, "Ya está bajo el objetivo")
        return _Compressed(
            f"{original:.2f} MB (sin cambios)", original, original, False
        )

    # Los intentos van a una carpeta oculta junto al destino: usan el mismo
    # disco que la salida (no el del sistema) y el ganador se publica con un
    # `os.replace` atómico, sin copiarlo.
    with tempfile.TemporaryDirectory(prefix=".pdf-tool-", dir=out.parent) as workdir:
        candidates = _Candidates(Path(workdir))

        def publish(note: str = "") -> _Compressed:
            assert candidates.best is not None
            os.replace(candidates.best, out)
            final = candidates.best_mb
            progress(1.0, f"Listo: {final:.2f} MB")
            return _Compressed(
                f"{original:.2f} MB → {final:.2f} MB"
                f"{_saved_label(original, final)}{note}",
                original,
                final,
                candidates.best_rasterized,
            )

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
                ),
                rasterizes=True,
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

    def one(path: Path, scoped: Progress) -> Outcome:
        out = output_path_for(path, target_mb, params.output_dir)
        try:
            done = _compress_one(path, out, target_mb, scoped, params.mode)
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
        return done.outcome(out)

    batch = run_batch(inputs, one, progress, all_failed="Ningún PDF pudo comprimirse.")
    outputs, total = batch.outputs, batch.total
    done_items = [item for item in batch.items if item.ok]
    total_original = sum(item.metrics["original_mb"] for item in done_items)
    total_final = sum(item.metrics["final_mb"] for item in done_items)
    saved_pct = (
        max(0.0, (total_original - total_final) / total_original * 100)
        if total_original
        else 0.0
    )
    metrics = {
        "original_mb": total_original,
        "final_mb": total_final,
        "saved_pct": saved_pct,
    }
    warnings = sorted({w for item in done_items for w in item.warnings})

    if total == 1:
        return ToolResult(
            outputs=outputs,
            summary=batch.items[0].message,
            warnings=warnings,
            metrics=metrics,
        )

    tail = f" ({saved_pct:.0f} % menos)" if saved_pct >= 0.5 else " (sin cambios)"
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
        warnings=warnings,
        metrics=metrics,
    )
