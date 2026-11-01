import os
from pathlib import Path

import pymupdf
import pytest

from pdftool import i18n


@pytest.fixture(autouse=True)
def _spanish(monkeypatch):
    """Los tests comparan textos en español salvo que pidan otro idioma.

    También el idioma «del sistema», para que la CLI no dependa del equipo
    donde corren los tests (en el CI sería inglés)."""
    monkeypatch.setattr(i18n, "_ui_language", lambda: "es-ES")
    i18n.use_locales_dir(None)
    i18n.set_language("es")
    yield
    i18n.use_locales_dir(None)
    i18n.set_language("es")


def _make_pdf(path: Path, *, pages: int = 1, image_px: int = 0) -> Path:
    with pymupdf.open() as doc:
        for _ in range(pages):
            page = doc.new_page(width=595, height=842)
            page.insert_text((72, 72), "Hola pdf-tool")
            if image_px:
                # Imagen RGB con bytes pseudo-aleatorios -> incompresible -> archivo grande.
                samples = os.urandom(image_px * image_px * 3)
                pix = pymupdf.Pixmap(pymupdf.csRGB, image_px, image_px, samples, 0)
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
