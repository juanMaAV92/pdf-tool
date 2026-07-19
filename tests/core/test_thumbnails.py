from pathlib import Path

import fitz

from pdftool.core.thumbnails import THUMBNAIL_HEIGHT_PX, render_thumbnail


def _pdf(path: Path, pages: int = 1) -> Path:
    with fitz.open() as doc:
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"pagina {i}")
        doc.save(str(path))
    return path


def _protected_pdf(path: Path) -> Path:
    with fitz.open() as doc:
        doc.new_page()
        doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw="x", user_pw="x")
    return path


def _img(path: Path, w: int = 120, h: int = 90) -> Path:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h))
    pix.clear_with(200)
    pix.save(str(path))
    return path


def _height(png: bytes) -> int:
    return fitz.Pixmap(png).height


def test_pdf_renders_at_default_height(tmp_path):
    png = render_thumbnail(_pdf(tmp_path / "a.pdf"))
    assert png is not None
    assert abs(_height(png) - THUMBNAIL_HEIGHT_PX) <= 1  # redondeo de pixmap


def test_custom_height(tmp_path):
    png = render_thumbnail(_pdf(tmp_path / "a.pdf"), height_px=96)
    assert png is not None
    assert abs(_height(png) - 96) <= 1


def test_image_renders(tmp_path):
    png = render_thumbnail(_img(tmp_path / "a.png"))
    assert png is not None
    assert abs(_height(png) - THUMBNAIL_HEIGHT_PX) <= 1


def test_second_page_renders(tmp_path):
    png = render_thumbnail(_pdf(tmp_path / "a.pdf", pages=2), page_index=1)
    assert png is not None


def test_protected_pdf_returns_none(tmp_path):
    assert render_thumbnail(_protected_pdf(tmp_path / "p.pdf")) is None


def test_corrupt_file_returns_none(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"no soy un pdf")
    assert render_thumbnail(bad) is None


def test_page_out_of_range_returns_none(tmp_path):
    assert render_thumbnail(_pdf(tmp_path / "a.pdf"), page_index=5) is None
