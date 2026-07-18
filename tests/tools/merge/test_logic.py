from pathlib import Path

import fitz
import pytest

from pdftool.tools.merge.logic import merge, output_path_for_merge
from pdftool.tools.merge.params import MergeParams


def _pdf(path: Path, pages: int, text: str) -> Path:
    with fitz.open() as doc:
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"{text}-{i}")
        doc.save(str(path))
    return path


def test_output_next_to_first_input(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    out = output_path_for_merge([a])
    assert out.parent == tmp_path
    assert out.name == "a_merged.pdf"


def test_output_never_equals_an_input(tmp_path):
    a = _pdf(tmp_path / "a_merged.pdf", 1, "A")
    out = output_path_for_merge([a])
    assert out != a


def test_empty_inputs_raises():
    with pytest.raises(ValueError):
        merge([], MergeParams())


def test_merge_sums_pages(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 2, "A")
    b = _pdf(tmp_path / "b.pdf", 3, "B")
    result = merge([a, b], MergeParams())
    out = result.outputs[0]
    assert out.exists()
    with fitz.open(str(out)) as d:
        assert d.page_count == 5


def test_merge_preserves_order(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "AAA")
    b = _pdf(tmp_path / "b.pdf", 1, "BBB")
    result = merge([b, a], MergeParams())  # b primero
    with fitz.open(str(result.outputs[0])) as d:
        first_page_text = d[0].get_text()
    assert "BBB" in first_page_text


def test_missing_file_raises(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    with pytest.raises(FileNotFoundError):
        merge([a, tmp_path / "nope.pdf"], MergeParams())


def test_progress_reaches_one(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    b = _pdf(tmp_path / "b.pdf", 1, "B")
    seen = []
    merge([a, b], MergeParams(), progress=lambda p, m: seen.append(p))
    assert seen and seen[-1] == 1.0


def test_output_uses_custom_name(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    out = output_path_for_merge([a], name="informe 2024")
    assert out == tmp_path / "informe 2024.pdf"


def test_custom_name_never_equals_an_input(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    out = output_path_for_merge([a], name="a")
    assert out == tmp_path / "a_1.pdf"


def test_merge_with_custom_name(tmp_path):
    a = _pdf(tmp_path / "a.pdf", 1, "A")
    b = _pdf(tmp_path / "b.pdf", 1, "B")
    result = merge([a, b], MergeParams(output_name="junto"))
    assert result.outputs[0].name == "junto.pdf"
    assert result.outputs[0].exists()
    assert "junto.pdf" in result.summary
