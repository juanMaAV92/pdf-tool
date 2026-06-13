from pathlib import Path

import pytest

from pdftool.tools.compress.logic import compress, output_path_for
from pdftool.tools.compress.params import CompressParams


def test_output_suffix_integer():
    p = output_path_for(Path("/x/doc.pdf"), 2.0)
    assert p.name == "doc_2MB.pdf"


def test_output_suffix_decimal():
    p = output_path_for(Path("/x/doc.pdf"), 2.5)
    assert p.name == "doc_2_5MB.pdf"


def test_output_suffix_strips_previous():
    p = output_path_for(Path("/x/doc_compressed_5MB.pdf"), 2.0)
    assert p.name == "doc_2MB.pdf"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        compress([Path("/no/such.pdf")], CompressParams())


def test_already_under_target_copies(small_pdf):
    result = compress([small_pdf], CompressParams(target_mb=50.0))
    assert result.outputs[0].exists()
    assert "sin cambios" in result.summary


def test_compress_reduces_size(big_pdf):
    original_mb = big_pdf.stat().st_size / (1024 * 1024)
    assert original_mb > 1.0  # la fixture es grande
    result = compress([big_pdf], CompressParams(target_mb=1.0))
    out = result.outputs[0]
    assert out.exists()
    assert out.stat().st_size < big_pdf.stat().st_size


def test_progress_is_reported(small_pdf):
    seen = []
    compress([small_pdf], CompressParams(target_mb=50.0),
             progress=lambda p, m: seen.append((p, m)))
    assert seen and seen[-1][0] == 1.0
