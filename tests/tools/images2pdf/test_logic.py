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


def test_output_next_to_image(tmp_path):
    out = output_path_for_images(tmp_path / "a.png")
    assert out == tmp_path / "a.pdf"


def test_output_avoids_existing_pdf(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"ya existe")
    out = output_path_for_images(tmp_path / "a.png")
    assert out == tmp_path / "a_1.pdf"


def test_one_pdf_per_image(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    b = _img(tmp_path / "b.jpg", 100, 100)
    c = _img(tmp_path / "c.png", 100, 100)
    res = images_to_pdf([a, b, c], ImagesToPdfParams())
    assert [o.name for o in res.outputs] == ["a.pdf", "b.pdf", "c.pdf"]
    assert res.summary == "3 imágenes convertidas"
    assert res.details == ["→ a.pdf", "→ b.pdf", "→ c.pdf"]
    for out in res.outputs:
        with fitz.open(str(out)) as d:
            assert d.page_count == 1


def test_page_keeps_image_proportions(tmp_path):
    wide = _img(tmp_path / "wide.png", 200, 100)   # apaisada (2:1)
    tall = _img(tmp_path / "tall.png", 100, 200)   # vertical (1:2)
    res = images_to_pdf([wide, tall], ImagesToPdfParams())
    with fitz.open(str(res.outputs[0])) as d:
        r0 = d[0].rect
    with fitz.open(str(res.outputs[1])) as d:
        r1 = d[0].rect
    assert r0.width / r0.height == pytest.approx(2.0, rel=0.02)
    assert r1.width / r1.height == pytest.approx(0.5, rel=0.02)


def test_single_image_has_no_details(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    res = images_to_pdf([a], ImagesToPdfParams())
    assert res.details is None
    assert res.summary == "Imagen convertida → a.pdf"


def test_unsupported_file_continues_batch(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    bad = tmp_path / "b.txt"
    bad.write_text("no soy una imagen")
    res = images_to_pdf([a, bad], ImagesToPdfParams())
    assert [o.name for o in res.outputs] == ["a.pdf"]
    assert res.summary == "1 de 2 imágenes convertidas"
    assert res.details[0] == "→ a.pdf"
    assert "Formato no soportado" in res.details[1]


def test_all_fail_raises(tmp_path):
    x = tmp_path / "x.txt"
    y = tmp_path / "y.txt"
    x.write_text("no")
    y.write_text("tampoco")
    with pytest.raises(ValueError):
        images_to_pdf([x, y], ImagesToPdfParams())


def test_single_unsupported_keeps_original_message(tmp_path):
    bad = tmp_path / "b.txt"
    bad.write_text("no soy una imagen")
    with pytest.raises(ValueError, match="Formato no soportado"):
        images_to_pdf([bad], ImagesToPdfParams())


def test_multi_progress_labels_and_completion(tmp_path):
    a = _img(tmp_path / "a.png", 100, 100)
    b = _img(tmp_path / "b.png", 100, 100)
    seen = []
    images_to_pdf([a, b], ImagesToPdfParams(),
                  progress=lambda p, m: seen.append((p, m)))
    assert seen[-1][0] == 1.0
    assert any(m.startswith("[1/2] a.png:") for _p, m in seen)
    assert any(m.startswith("[2/2] b.png:") for _p, m in seen)


def test_extension_case_insensitive(tmp_path):
    a = _img(tmp_path / "a.PNG", 100, 100)
    b = _img(tmp_path / "b.JPEG", 100, 100)
    res = images_to_pdf([a, b], ImagesToPdfParams())
    assert len(res.outputs) == 2


def test_corrupt_image_with_valid_extension_continues(tmp_path):
    ok = _img(tmp_path / "ok.png", 100, 100)
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"no soy un png")
    res = images_to_pdf([ok, bad], ImagesToPdfParams())
    assert [o.name for o in res.outputs] == ["ok.pdf"]
    assert res.summary == "1 de 2 imágenes convertidas"
    assert res.details[1] and not res.details[1].startswith("→")


def test_same_stem_in_one_batch_does_not_clobber(tmp_path):
    a_png = _img(tmp_path / "a.png", 100, 100)
    a_jpg = _img(tmp_path / "a.jpg", 100, 100)
    res = images_to_pdf([a_png, a_jpg], ImagesToPdfParams())
    assert [o.name for o in res.outputs] == ["a.pdf", "a_1.pdf"]
    assert all(o.exists() for o in res.outputs)
