from pathlib import Path

import pymupdf
import pytest

from pdftool.tools.compress.logic import (
    RASTERIZED_WARNING,
    compress,
    output_path_for,
)
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
    with pymupdf.open(out) as doc:
        assert len(doc) > 0


def test_progress_is_reported(small_pdf):
    seen = []
    compress(
        [small_pdf],
        CompressParams(target_mb=50.0),
        progress=lambda p, m: seen.append((p, m)),
    )
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


def test_preserve_mode_keeps_text_when_target_is_impossible(big_pdf):
    result = compress([big_pdf], CompressParams(target_mb=0.0001, mode="preserve"))

    with pymupdf.open(result.outputs[0]) as doc:
        assert "Hola pdf-tool" in doc[0].get_text()
    assert "contenido preservado" in result.summary


def _catalog_pdf(path: Path) -> Path:
    """Foto de mucha resolución mostrada pequeña (~580 ppp), como en un catálogo."""
    import os

    with pymupdf.open() as doc:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), "Catálogo pdf-tool")
        px = 1600
        pix = pymupdf.Pixmap(pymupdf.csRGB, px, px, os.urandom(px * px * 3), 0)
        page.insert_image(pymupdf.Rect(72, 100, 272, 300), pixmap=pix)
        doc.save(str(path))
    return path


def test_max_mode_reduces_images_before_rasterizing(tmp_path):
    """Si recomprimir las imágenes basta, `max` no convierte páginas en imagen:
    se conservan el texto y no hay aviso de rasterizado."""
    src = _catalog_pdf(tmp_path / "catalogo.pdf")
    assert src.stat().st_size > 5 * 1024 * 1024

    result = compress([src], CompressParams(target_mb=1.0))

    assert result.outputs[0].stat().st_size <= 1024 * 1024
    assert RASTERIZED_WARNING not in result.warnings
    with pymupdf.open(result.outputs[0]) as doc:
        assert "Catálogo pdf-tool" in doc[0].get_text()


# ---------------------------------------------------------------------------
# Fix 1: output path must never equal input path
# ---------------------------------------------------------------------------


def test_output_path_never_equals_input():
    """Comprimir a un tamaño que ya está en el nombre no puede devolver la entrada."""
    input_path = Path("/x/report_5MB.pdf")
    result = output_path_for(input_path, 5.0)
    assert result != input_path
    assert result.name == "report_5MB (1).pdf"


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
    compress(
        [src1, src2],
        CompressParams(target_mb=50.0),
        progress=lambda p, m: seen.append((p, m)),
    )
    assert seen and seen[-1][0] == 1.0


def test_compress_multiple_has_per_file_items(tmp_path, big_pdf):
    """Con varios archivos, result.items trae un resultado por entrada."""
    import shutil

    src1 = tmp_path / "uno.pdf"
    src2 = tmp_path / "dos.pdf"
    shutil.copy2(big_pdf, src1)
    shutil.copy2(big_pdf, src2)
    result = compress([src1, src2], CompressParams(target_mb=50.0))
    assert result.items is not None
    assert len(result.items) == 2
    assert all(item.ok for item in result.items)
    assert all("sin cambios" in item.message for item in result.items)


def test_compress_single_has_no_items(small_pdf):
    """Con un solo archivo no hace falta detalle por fila."""
    result = compress([small_pdf], CompressParams(target_mb=50.0))
    assert result.items is None


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


def test_output_avoids_an_existing_file(tmp_path):
    (tmp_path / "doc_2MB.pdf").write_bytes(b"previo")
    out = output_path_for(tmp_path / "doc.pdf", 2.0)
    assert out == tmp_path / "doc_2MB (1).pdf"


def test_stem_cleanup_absorbs_a_duplicate_suffix():
    """Recomprimir una salida ya desambiguada no arrastra el « (n)» al nombre."""
    out = output_path_for(Path("/x/doc_5MB (1).pdf"), 2.0)
    assert out.name == "doc_2MB.pdf"


def test_compress_does_not_overwrite_a_previous_output(tmp_path, big_pdf):
    import shutil

    src = tmp_path / "doc.pdf"
    shutil.copy2(big_pdf, src)
    (tmp_path / "doc_1MB.pdf").write_bytes(b"previo")

    result = compress([src], CompressParams(target_mb=1.0))

    assert result.outputs[0] == tmp_path / "doc_1MB (1).pdf"
    assert (tmp_path / "doc_1MB.pdf").read_bytes() == b"previo"


def test_compress_writes_to_output_dir(tmp_path, big_pdf):
    import shutil

    destino = tmp_path / "destino"
    destino.mkdir()
    src = tmp_path / "doc.pdf"
    shutil.copy2(big_pdf, src)

    res = compress([src], CompressParams(target_mb=1.0, output_dir=destino))

    assert res.outputs[0].parent == destino
    assert res.outputs[0].exists()


def test_corrupt_file_does_not_abort_the_batch(tmp_path, small_pdf):
    """Un PDF dañado queda reportado; el resto del lote se procesa."""
    import shutil

    good1 = shutil.copy2(small_pdf, tmp_path / "uno.pdf")
    corrupt = tmp_path / "roto.pdf"
    corrupt.write_bytes(b"esto no es un pdf" * 100)
    good2 = shutil.copy2(small_pdf, tmp_path / "dos.pdf")

    result = compress(
        [Path(good1), corrupt, Path(good2)], CompressParams(target_mb=0.0001)
    )

    assert [item.ok for item in result.items] == [True, False, True]
    assert result.items[1].output_path is None
    assert len(result.outputs) == 2
    assert result.summary.startswith("2 de 3 archivos")


@pytest.mark.parametrize(
    "content",
    [b"esto no es un pdf\n", b"%PDF-1.7\n1 0 obj\n<</Type/Catalog"],
    ids=["texto", "truncado"],
)
def test_invalid_file_under_target_is_reported_not_copied(tmp_path, content):
    """Pesar menos que el objetivo no exime de abrirlo: si no es un PDF válido,
    falla en vez de copiarse y reportarse como «sin cambios»."""
    bad = tmp_path / "roto.pdf"
    bad.write_bytes(content)

    with pytest.raises(Exception):  # noqa: B017 - el error lo traduce run_batch
        compress([bad], CompressParams(target_mb=50.0))
    assert list(tmp_path.iterdir()) == [bad]


def test_invalid_file_under_target_fails_its_batch_item(tmp_path, small_pdf):
    import shutil

    good = shutil.copy2(small_pdf, tmp_path / "uno.pdf")
    bad = tmp_path / "roto.pdf"
    bad.write_bytes(b"esto no es un pdf\n")

    result = compress([Path(good), bad], CompressParams(target_mb=50.0))

    assert [item.ok for item in result.items] == [True, False]
    assert result.items[1].output_path is None


def test_failed_file_leaves_no_partial_output(tmp_path, big_pdf, monkeypatch):
    """Si un intento falla tras escribir una salida intermedia, se retira."""
    import pdftool.tools.compress.logic as logic

    def boom(*_a, **_k):
        raise RuntimeError("fallo a mitad")

    monkeypatch.setattr(logic, "_rerender", boom)
    with pytest.raises(RuntimeError):
        compress([big_pdf], CompressParams(target_mb=0.0001))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["big.pdf"]


def test_cancellation_stops_the_batch(tmp_path, small_pdf):
    import shutil

    from pdftool.core.jobs import JobCancelled

    a = shutil.copy2(small_pdf, tmp_path / "a.pdf")
    b = shutil.copy2(small_pdf, tmp_path / "b.pdf")

    def cancel(_p, _m):
        raise JobCancelled()

    with pytest.raises(JobCancelled):
        compress([Path(a), Path(b)], CompressParams(target_mb=50.0), progress=cancel)


def test_rerender_bounds_the_pixmap_of_a_huge_page(tmp_path):
    """El zoom mínimo de 0.5 convertía una página enorme en decenas de MP."""
    from pdftool.tools.compress.logic import _rerender

    src = tmp_path / "poster.pdf"
    with pymupdf.open() as doc:
        doc.new_page(width=14400, height=14400)
        doc.save(str(src))
    dst = tmp_path / "out.pdf"

    _rerender(src, dst, max_dimension=600, jpg_quality=25)

    with pymupdf.open(str(dst)) as doc:
        xref = doc[0].get_images()[0][0]
        pix = pymupdf.Pixmap(doc, xref)
        assert max(pix.width, pix.height) <= 600


def _pages_pdf(path, n):
    with pymupdf.open() as doc:
        for i in range(n):
            doc.new_page().insert_text((72, 72), f"pagina {i}")
        doc.save(str(path))
    return path


def test_rerender_reports_progress_per_page(tmp_path):
    from pdftool.tools.compress.logic import _rerender

    src = _pages_pdf(tmp_path / "doc.pdf", 4)
    seen = []
    _rerender(
        src,
        tmp_path / "out.pdf",
        max_dimension=600,
        jpg_quality=25,
        progress=lambda p, m: seen.append(p),
    )
    assert len(seen) >= 4
    assert seen == sorted(seen)


def test_cancelling_during_rerender_leaves_no_output(tmp_path, big_pdf):
    from pdftool.core.jobs import JobCancelled

    calls = []

    def cancel_on_rerender(pct, msg):
        calls.append(msg)
        if "página" in msg:
            raise JobCancelled()

    with pytest.raises(JobCancelled):
        compress(
            [big_pdf], CompressParams(target_mb=0.0001), progress=cancel_on_rerender
        )
    assert sorted(p.name for p in big_pdf.parent.iterdir()) == ["big.pdf"]


def test_progress_messages_avoid_technical_jargon(big_pdf):
    seen = []
    compress(
        [big_pdf],
        CompressParams(target_mb=0.0001),
        progress=lambda p, m: seen.append(m),
    )
    joined = " ".join(seen).lower()
    for jargon in ("dpi", "px", "intento", "mejor esfuerzo"):
        assert jargon not in joined


def test_only_the_final_result_is_written_to_the_destination(big_pdf, monkeypatch):
    import pdftool.core.atomic as atomic

    published = []
    real_replace = atomic.os.replace

    def counting_replace(src, dst):
        if Path(dst).parent == big_pdf.parent:
            published.append(Path(dst).name)
        return real_replace(src, dst)

    monkeypatch.setattr(atomic.os, "replace", counting_replace)
    result = compress([big_pdf], CompressParams(target_mb=0.0001))
    assert published == [result.outputs[0].name]


def test_best_effort_summary_explains_the_outcome(big_pdf):
    result = compress([big_pdf], CompressParams(target_mb=0.0001))
    assert "no se alcanzó el objetivo" in result.summary
    assert "versión más pequeña" in result.summary


def test_cancel_after_publishing_keeps_the_finished_file(big_pdf):
    """«Los archivos ya terminados se conservan»: también el último."""
    from pdftool.core.jobs import JobCancelled

    def cancel_when_done(_pct, msg):
        if msg.startswith("Listo"):
            raise JobCancelled()

    with pytest.raises(JobCancelled):
        compress([big_pdf], CompressParams(target_mb=0.0001), progress=cancel_when_done)
    outputs = [p for p in big_pdf.parent.iterdir() if p.name != "big.pdf"]
    assert len(outputs) == 1


def test_attempts_live_next_to_the_destination_and_are_cleaned(
    tmp_path, big_pdf, monkeypatch
):
    """Los intentos usan el disco del destino (no el del sistema) y no quedan."""
    import pdftool.tools.compress.logic as logic

    workdirs = []
    real_init = logic._Candidates.__init__

    def spy(self, workdir):
        workdirs.append(workdir)
        real_init(self, workdir)

    monkeypatch.setattr(logic._Candidates, "__init__", spy)
    out_dir = tmp_path / "salida"
    out_dir.mkdir()
    result = compress([big_pdf], CompressParams(target_mb=0.0001, output_dir=out_dir))

    assert workdirs[0].parent == out_dir
    assert workdirs[0].name.startswith(".pdf-tool-")
    assert [p.name for p in out_dir.iterdir()] == [result.outputs[0].name]


_RASTER = "convirtieron en imagen"


def test_rasterizing_is_reported_with_size_metrics(big_pdf):
    result = compress([big_pdf], CompressParams(target_mb=0.0001))
    assert any(_RASTER in w for w in result.warnings)
    m = result.metrics
    assert m["original_mb"] > m["final_mb"] > 0
    assert m["saved_pct"] == pytest.approx(
        (m["original_mb"] - m["final_mb"]) / m["original_mb"] * 100
    )
    assert f"{m['saved_pct']:.0f} % menos" in result.summary


def test_preserve_mode_never_warns_about_rasterizing(big_pdf):
    result = compress([big_pdf], CompressParams(target_mb=0.0001, mode="preserve"))
    assert not any(_RASTER in w for w in result.warnings)


def test_file_already_under_target_has_no_warnings(small_pdf):
    result = compress([small_pdf], CompressParams(target_mb=50.0))
    assert result.warnings == []
    assert result.metrics["saved_pct"] == 0


def test_batch_rows_carry_their_own_warnings(tmp_path, big_pdf, small_pdf):
    import shutil

    big = Path(shutil.copy2(big_pdf, tmp_path / "grande.pdf"))
    small = Path(shutil.copy2(small_pdf, tmp_path / "chico.pdf"))
    # ⅙ del original: recomprimir solo las imágenes no llega (~¼), así que
    # `max` tiene que convertir páginas en imagen y avisarlo.
    target = (big.stat().st_size / (1024 * 1024)) / 6
    result = compress([big, small], CompressParams(target_mb=target))
    big_row, small_row = result.items
    assert any(_RASTER in w for w in big_row.warnings)
    assert small_row.warnings == ()
    assert "saved_pct" in big_row.metrics


def test_rerender_in_chunks_keeps_every_page(tmp_path, monkeypatch):
    """Guardar por bloques (para acotar memoria) no pierde ni duplica páginas."""
    import pdftool.tools.compress.logic as logic

    monkeypatch.setattr(logic, "_RERENDER_CHUNK", 2)
    src = _pages_pdf(tmp_path / "doc.pdf", 5)
    dst = tmp_path / "out.pdf"
    seen = []

    logic._rerender(
        src,
        dst,
        max_dimension=400,
        jpg_quality=40,
        progress=lambda p, m: seen.append(p),
    )

    with pymupdf.open(str(dst)) as doc:
        assert doc.page_count == 5
        assert all(len(page.get_images()) == 1 for page in doc)
    assert seen[-1] == 1.0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doc.pdf", "out.pdf"]


def test_chunked_output_is_compacted(tmp_path, monkeypatch):
    """Los guardados incrementales se compactan: no crece por cada bloque."""
    import pdftool.tools.compress.logic as logic

    src = _pages_pdf(tmp_path / "doc.pdf", 6)
    whole, chunked = tmp_path / "whole.pdf", tmp_path / "chunked.pdf"
    logic._rerender(src, whole, max_dimension=400, jpg_quality=40)
    monkeypatch.setattr(logic, "_RERENDER_CHUNK", 2)
    logic._rerender(src, chunked, max_dimension=400, jpg_quality=40)

    assert chunked.stat().st_size <= whole.stat().st_size * 1.05
