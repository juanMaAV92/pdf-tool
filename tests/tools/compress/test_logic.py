from pathlib import Path

import fitz
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
    with fitz.open(out) as doc:
        assert len(doc) > 0


def test_progress_is_reported(small_pdf):
    seen = []
    compress([small_pdf], CompressParams(target_mb=50.0),
             progress=lambda p, m: seen.append((p, m)))
    assert seen and seen[-1][0] == 1.0


def test_empty_inputs_raises():
    with pytest.raises(ValueError, match="inputs está vacío"):
        compress([], CompressParams())


def test_best_effort_branch(big_pdf):
    """Impossibly small target exercises the 'no se alcanzó el objetivo' path."""
    result = compress([big_pdf], CompressParams(target_mb=0.0001))
    out = result.outputs[0]
    assert out.exists()
    assert "no se alcanzó el objetivo" in result.summary


# ---------------------------------------------------------------------------
# Fix 1: output path must never equal input path
# ---------------------------------------------------------------------------

def test_output_path_never_equals_input():
    """When input encodes the target size, output must not collide with input."""
    input_path = Path("/x/report_5MB.pdf")
    result = output_path_for(input_path, 5.0)
    assert result != input_path, "output_path_for must not return the input path itself"
    assert result.name == "report_5MB_1.pdf", (
        f"expected 'report_5MB_1.pdf', got '{result.name}'"
    )


def test_compress_multiple_files(tmp_path, big_pdf):
    """compress() procesa cada PDF de la lista y devuelve una salida por archivo."""
    import shutil

    src1 = tmp_path / "uno.pdf"
    src2 = tmp_path / "dos.pdf"
    shutil.copy2(big_pdf, src1)
    shutil.copy2(big_pdf, src2)

    result = compress([src1, src2], CompressParams(target_mb=1.0))

    assert len(result.outputs) == 2
    assert all(out.exists() for out in result.outputs)
    assert result.outputs[0].parent == src1.parent
    assert result.outputs[1].parent == src2.parent
    assert "2 archivos" in result.summary


def test_compress_multiple_missing_file_raises(tmp_path, big_pdf):
    """Si alguno de los archivos no existe, se avisa antes de procesar."""
    import shutil

    src = tmp_path / "existe.pdf"
    shutil.copy2(big_pdf, src)
    with pytest.raises(FileNotFoundError):
        compress([src, tmp_path / "no_existe.pdf"], CompressParams(target_mb=1.0))


def test_compress_multiple_progress_reaches_one(tmp_path, big_pdf):
    import shutil

    src1 = tmp_path / "a.pdf"
    src2 = tmp_path / "b.pdf"
    shutil.copy2(big_pdf, src1)
    shutil.copy2(big_pdf, src2)
    seen = []
    compress([src1, src2], CompressParams(target_mb=50.0),
             progress=lambda p, m: seen.append((p, m)))
    assert seen and seen[-1][0] == 1.0


def test_compress_multiple_has_per_file_details(tmp_path, big_pdf):
    """Con varios archivos, result.details trae una etiqueta por salida."""
    import shutil

    src1 = tmp_path / "uno.pdf"
    src2 = tmp_path / "dos.pdf"
    shutil.copy2(big_pdf, src1)
    shutil.copy2(big_pdf, src2)
    result = compress([src1, src2], CompressParams(target_mb=50.0))
    assert result.details is not None
    assert len(result.details) == 2
    assert all("sin cambios" in d for d in result.details)


def test_compress_single_has_no_details(small_pdf):
    """Con un solo archivo no hace falta detalle por fila."""
    result = compress([small_pdf], CompressParams(target_mb=50.0))
    assert result.details is None


def test_compress_no_self_overwrite(tmp_path, big_pdf):
    """compress() must not raise and must produce a different output path than input."""
    import shutil

    # Copy big_pdf to a name that already encodes the target label
    src = tmp_path / "doc_1MB.pdf"
    shutil.copy2(big_pdf, src)

    result = compress([src], CompressParams(target_mb=1.0))
    out = result.outputs[0]
    assert out != src, "Output path must differ from input path"
    assert out.exists(), "Output file must exist"
