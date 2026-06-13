import os
from pathlib import Path

import fitz
import pytest


def _make_pdf(path: Path, *, pages: int = 1, image_px: int = 0) -> Path:
    with fitz.open() as doc:
        for _ in range(pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), "Hola pdf-tool")
            if image_px:
                # Imagen RGB con bytes pseudo-aleatorios -> incompresible -> archivo grande.
                samples = os.urandom(image_px * image_px * 3)
                pix = fitz.Pixmap(fitz.csRGB, image_px, image_px, samples, 0)
                page.insert_image(page.rect, pixmap=pix)
        doc.save(str(path))
    return path


@pytest.fixture
def small_pdf(tmp_path) -> Path:
    return _make_pdf(tmp_path / "small.pdf", pages=1)


@pytest.fixture
def big_pdf(tmp_path) -> Path:
    # ~varios MB por la imagen ruidosa grande.
    return _make_pdf(tmp_path / "big.pdf", pages=2, image_px=1600)
