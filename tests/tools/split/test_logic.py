from pathlib import Path

import fitz
import pytest

from pdftool.tools.split.logic import (
    parse_ranges,
    resolve_ranges,
    split,
)
from pdftool.tools.split.params import SplitParams


def _pdf(path: Path, pages: int) -> Path:
    """PDF con texto identificable por página: 'PAGE-0', 'PAGE-1', ..."""
    with fitz.open() as doc:
        for i in range(pages):
            page = doc.new_page()
            page.insert_text((72, 72), f"PAGE-{i}")
        doc.save(str(path))
    return path


# --- parse_ranges: sintaxis pura (sin saber el total de páginas) ---

def test_parse_single_page():
    assert parse_ranges("5") == [(5, 5)]


def test_parse_closed_range():
    assert parse_ranges("1-3") == [(1, 3)]


def test_parse_open_end():
    assert parse_ranges("8-") == [(8, None)]


def test_parse_open_start():
    assert parse_ranges("-4") == [(None, 4)]


def test_parse_multiple_comma_separated():
    assert parse_ranges("1-3, 5, 8-") == [(1, 3), (5, 5), (8, None)]


def test_parse_whitespace_tolerant():
    assert parse_ranges("  1 - 3 , 5 ") == [(1, 3), (5, 5)]


def test_parse_skips_trailing_comma():
    assert parse_ranges("1-3,") == [(1, 3)]


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_ranges("")


def test_parse_blank_raises():
    with pytest.raises(ValueError):
        parse_ranges("   ")


def test_parse_inverted_range_raises():
    with pytest.raises(ValueError):
        parse_ranges("5-2")


def test_parse_zero_raises():
    with pytest.raises(ValueError):
        parse_ranges("0")


def test_parse_non_numeric_raises():
    with pytest.raises(ValueError):
        parse_ranges("abc")


def test_parse_too_many_dashes_raises():
    with pytest.raises(ValueError):
        parse_ranges("1-2-3")


# --- resolve_ranges: contra el total real de páginas ---

def test_resolve_fills_open_ends():
    parsed = parse_ranges("8-, -4")
    assert resolve_ranges(parsed, 10) == [(8, 10), (1, 4)]


def test_resolve_out_of_bounds_raises():
    with pytest.raises(ValueError):
        resolve_ranges(parse_ranges("12"), 10)


def test_resolve_open_end_out_of_bounds_raises():
    with pytest.raises(ValueError):
        resolve_ranges(parse_ranges("8-"), 5)


# --- split: genera los PDFs ---

def test_split_empty_inputs_raises():
    with pytest.raises(ValueError):
        split([], SplitParams(mode="ranges", ranges="1"))


def test_split_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        split([tmp_path / "nope.pdf"], SplitParams(mode="ranges", ranges="1"))


def test_split_ranges_creates_one_file_per_range(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 10)
    result = split([src], SplitParams(mode="ranges", ranges="1-3, 5"))
    assert len(result.outputs) == 2
    with fitz.open(str(result.outputs[0])) as d:
        assert d.page_count == 3
    with fitz.open(str(result.outputs[1])) as d:
        assert d.page_count == 1


def test_split_ranges_keeps_correct_pages(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 10)
    result = split([src], SplitParams(mode="ranges", ranges="5"))
    with fitz.open(str(result.outputs[0])) as d:
        assert "PAGE-4" in d[0].get_text()  # página 5 (1-indexed) == índice 4


def test_split_single_page_per_file(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 4)
    result = split([src], SplitParams(mode="single"))
    assert len(result.outputs) == 4
    for out in result.outputs:
        with fitz.open(str(out)) as d:
            assert d.page_count == 1


def test_split_every_n_pages(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 10)
    result = split([src], SplitParams(mode="every", every_n=4))
    # 10 páginas en bloques de 4 -> 4, 4, 2
    assert len(result.outputs) == 3
    counts = []
    for out in result.outputs:
        with fitz.open(str(out)) as d:
            counts.append(d.page_count)
    assert counts == [4, 4, 2]


def test_outputs_next_to_original(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 4)
    result = split([src], SplitParams(mode="single"))
    for out in result.outputs:
        assert out.parent == tmp_path
        assert out.exists()


def test_progress_reaches_one(tmp_path):
    src = _pdf(tmp_path / "doc.pdf", 4)
    seen = []
    split([src], SplitParams(mode="single"), progress=lambda p, m: seen.append(p))
    assert seen and seen[-1] == 1.0
