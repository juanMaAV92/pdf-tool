from pathlib import Path

import fitz
import pytest
from pydantic import ValidationError

from pdftool.tools.watermark.logic import output_path_for_watermark, watermark
from pdftool.tools.watermark.params import WatermarkParams


def _pdf(path: Path, pages: int = 1, text: str = "Hola") -> Path:
    with fitz.open() as doc:
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(str(path))
    return path


def test_output_next_to_input(tmp_path):
    a = _pdf(tmp_path / "doc.pdf")
    out = output_path_for_watermark(a)
    assert out.parent == tmp_path
    assert out.name == "doc_marca.pdf"


def test_empty_text_rejected():
    with pytest.raises(ValidationError):
        WatermarkParams(text="")


def test_opacity_out_of_range_rejected():
    with pytest.raises(ValidationError):
        WatermarkParams(text="x", opacity=0)
    with pytest.raises(ValidationError):
        WatermarkParams(text="x", opacity=1.5)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        watermark([Path("/no/such.pdf")], WatermarkParams(text="X"))


def test_empty_inputs_raises():
    with pytest.raises(ValueError):
        watermark([], WatermarkParams(text="X"))


def test_watermark_adds_text_and_keeps_pages(tmp_path):
    a = _pdf(tmp_path / "doc.pdf", pages=2, text="Contenido")
    result = watermark([a], WatermarkParams(text="SECRETO", opacity=0.2))
    out = result.outputs[0]
    assert out.exists()
    with fitz.open(str(out)) as d:
        assert d.page_count == 2
        page_text = d[0].get_text()
    assert "SECRETO" in page_text


def test_progress_reaches_one(tmp_path):
    a = _pdf(tmp_path / "doc.pdf")
    seen = []
    watermark([a], WatermarkParams(text="X"), progress=lambda p, m: seen.append(p))
    assert seen and seen[-1] == 1.0


def test_output_avoids_an_existing_file(tmp_path):
    a = _pdf(tmp_path / "doc.pdf")
    (tmp_path / "doc_marca.pdf").write_bytes(b"previo")
    assert output_path_for_watermark(a) == tmp_path / "doc_marca (1).pdf"


def test_watermark_does_not_overwrite_a_previous_output(tmp_path):
    a = _pdf(tmp_path / "doc.pdf")
    (tmp_path / "doc_marca.pdf").write_bytes(b"previo")

    res = watermark([a], WatermarkParams(text="BORRADOR"))

    assert res.outputs[0] == tmp_path / "doc_marca (1).pdf"
    assert (tmp_path / "doc_marca.pdf").read_bytes() == b"previo"


def test_watermark_writes_to_output_dir(tmp_path):
    destino = tmp_path / "destino"
    destino.mkdir()
    a = _pdf(tmp_path / "doc.pdf")

    res = watermark([a], WatermarkParams(text="BORRADOR", output_dir=destino))

    assert res.outputs[0] == destino / "doc_marca.pdf"
    assert res.outputs[0].exists()


def test_huge_page_bounds_the_number_of_stamps(tmp_path, monkeypatch):
    """Los bucles del mosaico crecían con el tamaño de la página."""
    src = tmp_path / "poster.pdf"
    with fitz.open() as doc:
        doc.new_page(width=14400, height=14400)
        doc.save(str(src))
    calls = []
    original = fitz.Page.insert_text

    def counting(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    import pdftool.tools.watermark.logic as logic

    monkeypatch.setattr(logic, "_MAX_STAMPS_PER_PAGE", 200)
    monkeypatch.setattr(fitz.Page, "insert_text", counting)
    watermark([src], WatermarkParams(text="X", font_size=8))
    assert 0 < len(calls) <= 200


@pytest.mark.parametrize("size", [(595, 842), (612, 792), (842, 1191)])
def test_cap_does_not_change_spacing_on_real_page_sizes(size):
    from pdftool.tools.watermark.logic import _grid_steps

    text_w = fitz.get_text_length("X", fontsize=8)
    step_x, step_y = max(text_w + 16, 32), 32
    assert _grid_steps(fitz.Rect(0, 0, *size), step_x, step_y, text_w) == (
        step_x,
        step_y,
    )
