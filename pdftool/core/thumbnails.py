from __future__ import annotations

from pathlib import Path

import fitz

THUMBNAIL_HEIGHT_PX = 56


def render_thumbnail(path: Path, page_index: int = 0,
                     height_px: int = THUMBNAIL_HEIGHT_PX) -> bytes | None:
    """PNG de la página `page_index` a `height_px` de alto; None si no se puede.

    El fallo (protegido, corrupto, página inexistente) es un estado esperado del
    dominio — el consumidor muestra un icono genérico — por eso devuelve None en
    vez de lanzar. `page_index` existe para las futuras vistas de páginas
    (rotar/reordenar/dividir); hoy solo se consume con 0.
    """
    try:
        with fitz.open(str(path)) as doc:
            if doc.needs_pass or not 0 <= page_index < doc.page_count:
                return None
            page = doc[page_index]
            if page.rect.height <= 0 or page.rect.width <= 0:
                return None
            zoom = height_px / page.rect.height
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            return pix.tobytes("png")
    except Exception:  # corrupto/ilegible: estado esperado, no excepción
        return None
