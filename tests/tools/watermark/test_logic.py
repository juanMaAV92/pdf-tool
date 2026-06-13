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
