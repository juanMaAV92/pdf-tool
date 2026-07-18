from pathlib import Path

import fitz
import pytest

from pdftool.tools.images2pdf.logic import images_to_pdf, output_path_for_images
from pdftool.tools.images2pdf.params import ImagesToPdfParams


def _img(path: Path, w: int, h: int) -> Path:
    """Imagen sólida del tamaño pedido; el formato lo decide la extensión."""
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h))
    pix.clear_with(200)
    pix.save(str(path))
    return path


def test_empty_inputs_raises():
    with pytest.raises(ValueError):
        images_to_pdf([], ImagesToPdfParams())


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        images_to_pdf([tmp_path / "nope.png"], ImagesToPdfParams())


def test_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "file.txt"
    bad.write_text("not an image")
    with pytest.raises(ValueError):
        images_to_pdf([bad], ImagesToPdfParams())


def test_one_page_per_image(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    b = _img(tmp_path / "b.jpg", 100, 100)
    c = _img(tmp_path / "c.png", 100, 100)
    result = images_to_pdf([a, b, c], ImagesToPdfParams())
    with fitz.open(str(result.outputs[0])) as d:
        assert d.page_count == 3


def test_page_keeps_image_proportions_and_order(tmp_path):
    wide = _img(tmp_path / "wide.png", 200, 100)   # apaisada (2:1)
    tall = _img(tmp_path / "tall.png", 100, 200)   # vertical (1:2)
    result = images_to_pdf([wide, tall], ImagesToPdfParams())
    with fitz.open(str(result.outputs[0])) as d:
        r0, r1 = d[0].rect, d[1].rect
    assert r0.width / r0.height == pytest.approx(2.0, rel=0.02)
    assert r1.width / r1.height == pytest.approx(0.5, rel=0.02)


def test_extension_case_insensitive(tmp_path):
    a = _img(tmp_path / "a.PNG", 100, 100)
    b = _img(tmp_path / "b.JPEG", 100, 100)
    result = images_to_pdf([a, b], ImagesToPdfParams())
    with fitz.open(str(result.outputs[0])) as d:
        assert d.page_count == 2


def test_single_output_file(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    b = _img(tmp_path / "b.png", 100, 100)
    result = images_to_pdf([a, b], ImagesToPdfParams())
    assert len(result.outputs) == 1


def test_output_next_to_first_image(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    result = images_to_pdf([a], ImagesToPdfParams())
    out = result.outputs[0]
    assert out.parent == tmp_path
    assert out.suffix == ".pdf"
    assert out.exists()


def test_output_does_not_overwrite_existing_pdf(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    (tmp_path / "a.pdf").write_text("existente")  # ya hay un a.pdf
    out = output_path_for_images([a])
    assert out != tmp_path / "a.pdf"


def test_progress_reaches_one(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    b = _img(tmp_path / "b.png", 100, 100)
    seen = []
    images_to_pdf([a, b], ImagesToPdfParams(), progress=lambda p, m: seen.append(p))
    assert seen and seen[-1] == 1.0


def test_output_uses_custom_name(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    out = output_path_for_images([a], name="álbum")
    assert out == tmp_path / "álbum.pdf"


def test_custom_name_avoids_existing_pdf(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    (tmp_path / "álbum.pdf").write_bytes(b"ya existe")
    out = output_path_for_images([a], name="álbum")
    assert out == tmp_path / "álbum_1.pdf"


def test_images_to_pdf_with_custom_name(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    result = images_to_pdf([a], ImagesToPdfParams(output_name="álbum"))
    assert result.outputs[0].name == "álbum.pdf"
    assert result.outputs[0].exists()
