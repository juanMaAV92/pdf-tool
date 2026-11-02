"""Motor de `organize`.

`fixtures/chrome_tagged.pdf` es un PDF real, con etiquetas, `/Dests` e índice:
chrome --headless=new --no-pdf-header-footer --generate-pdf-document-outline \\
    --print-to-pdf=chrome_tagged.pdf file://$PWD/chrome_tagged.html
"""

import hashlib
import random
import shutil
from pathlib import Path

import pymupdf
import pytest

from pdftool.core.errors import UserError
from pdftool.core.pages import serialize_plan
from pdftool.tools.organize import logic
from pdftool.tools.organize.logic import organize, read_page_count
from pdftool.tools.organize.params import OrganizeParams

CHROME = Path(__file__).parents[2] / "fixtures" / "chrome_tagged.pdf"


def _pdf(path: Path, pages: int = 4) -> Path:
    with pymupdf.open() as doc:
        for number in range(1, pages + 1):
            doc.new_page(width=300, height=400).insert_text(
                (50, 50), f"TEXT-{number:04d}."
            )
        doc.save(path)
    return path


def _content_of(path: Path, page: int) -> bytes:
    """El flujo de contenido tal cual: el texto no aparece legible en el archivo."""
    with pymupdf.open(path) as doc:
        return doc[page - 1].read_contents()


def _run(path: Path, pages: str, **kwargs):
    return organize([path], OrganizeParams(pages=pages, **kwargs))


def _texts(path: Path) -> list[str]:
    with pymupdf.open(path) as doc:
        return [page.get_text().strip() for page in doc]


def _page_objects(path: Path) -> int:
    with pymupdf.open(path) as doc:
        return sum(
            doc.xref_get_key(xref, "Type") == ("name", "/Page")
            for xref in range(1, doc.xref_length())
        )


def _all_decoded(path: Path) -> bytes:
    """El archivo con todos sus objetos y flujos descomprimidos."""
    with pymupdf.open(path) as doc:
        return doc.tobytes(expand=255, no_new_id=True)


# ---------------------------------------------------------------------------
# Plan -> páginas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pages", "expected"),
    [
        ("end-1", [4, 3, 2, 1]),
        ("1,3-", [1, 3, 4]),
        ("3,1-2,2", [3, 1, 2, 2]),
        ("2", [2]),
        ("4,4,4", [4, 4, 4]),
        ("1-4", [1, 2, 3, 4]),
    ],
)
def test_output_follows_the_plan(tmp_path, pages, expected):
    src = _pdf(tmp_path / "a.pdf")
    result = _run(src, pages)
    assert _texts(result.outputs[0]) == [f"TEXT-{n:04d}." for n in expected]


def test_random_plans_keep_order_and_rotation(tmp_path):
    src = _pdf(tmp_path / "a.pdf", pages=12)
    rng = random.Random(7)
    for _ in range(25):
        plan = [
            (rng.randint(1, 12), rng.choice((0, 90, 180, 270)))
            for _ in range(rng.randint(1, 20))
        ]
        output = _run(src, serialize_plan(plan)).outputs[0]
        assert _texts(output) == [f"TEXT-{p:04d}." for p, _ in plan]
        with pymupdf.open(output) as doc:
            assert [page.rotation for page in doc] == [r for _, r in plan]
        assert _page_objects(output) == len(plan)
        output.unlink()


def test_rotation_is_relative_to_the_page(tmp_path):
    src = tmp_path / "a.pdf"
    with pymupdf.open() as doc:
        doc.new_page().set_rotation(90)
        doc.save(src)
    with pymupdf.open(_run(src, "1@90").outputs[0]) as doc:
        assert doc[0].rotation == 180


def test_copies_rotate_independently(tmp_path):
    src = _pdf(tmp_path / "a.pdf", pages=1)
    with pymupdf.open(_run(src, "1,1@90,1@180").outputs[0]) as doc:
        assert [page.rotation for page in doc] == [0, 90, 180]


def test_named_output_never_overwrites_and_goes_to_output_dir(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    first = _run(src, "1").outputs[0]
    second = _run(src, "1").outputs[0]
    assert first.name == "a_páginas.pdf"
    assert second.name == "a_páginas (1).pdf"
    out = tmp_path / "out"
    out.mkdir()
    assert _run(src, "1", output_dir=out).outputs[0].parent == out


def test_original_is_untouched(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    _run(src, "end-1")
    assert hashlib.sha256(src.read_bytes()).hexdigest() == before


def test_metrics_and_summary(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    result = _run(src, "1,2")
    assert result.metrics["pages_in"] == 4
    assert result.metrics["pages_out"] == 2
    assert result.metrics["bytes_in"] == src.stat().st_size
    assert result.metrics["bytes_out"] == result.outputs[0].stat().st_size
    assert "a_páginas.pdf" in result.summary
    assert "2 páginas" in result.summary


def test_invalid_plan_leaves_nothing(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    with pytest.raises(UserError):
        _run(src, "9")
    assert [p.name for p in tmp_path.iterdir()] == ["a.pdf"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _run(tmp_path / "nope.pdf", "1")


# ---------------------------------------------------------------------------
# Avisos
# ---------------------------------------------------------------------------


def test_identity_plan_warns_but_runs(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    result = _run(src, "1-4")
    assert result.outputs[0].exists()
    assert result.warnings == ["El plan no cambia nada: es una copia."]


def test_plain_edit_has_no_warnings(tmp_path):
    assert _run(_pdf(tmp_path / "a.pdf"), "2,1,3-").warnings == []


def test_attachments_warn_only_when_pages_leave(tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    with pymupdf.open(src) as doc:
        doc.embfile_add("note.txt", b"attached")
        doc.saveIncr()
    assert not any("adjuntos" in w for w in _run(src, "end-1").warnings)
    assert any("adjuntos" in w for w in _run(src, "1").warnings)


def test_signature_fields_warn_on_any_edit(tmp_path, monkeypatch):
    src = _pdf(tmp_path / "a.pdf")
    monkeypatch.setattr(pymupdf.Document, "get_sigflags", lambda _self: 3)
    assert any("firma" in w for w in _run(src, "2,1,3-").warnings)


# ---------------------------------------------------------------------------
# Contraseña y restricciones
# ---------------------------------------------------------------------------


def _encrypted(path: Path, *, user_pw: str = "") -> Path:
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50, 50), "ONE")
        doc.new_page().insert_text((50, 50), "TWO")
        doc.save(
            path,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="owner",
            user_pw=user_pw,
            permissions=pymupdf.PDF_PERM_ACCESSIBILITY,
        )
    return path


def test_password_is_refused_on_read_and_on_run(tmp_path):
    src = _encrypted(tmp_path / "locked.pdf", user_pw="secret")
    with pytest.raises(UserError, match="Proteger PDF"):
        read_page_count(src)
    with pytest.raises(UserError, match="Proteger PDF"):
        _run(src, "1")


def test_owner_restrictions_are_kept(tmp_path):
    src = _encrypted(tmp_path / "restricted.pdf")
    output = _run(src, "2,1").outputs[0]
    with pymupdf.open(output) as doc, pymupdf.open(src) as original:
        assert doc.is_encrypted or doc.metadata["encryption"]
        assert doc.permissions == original.permissions
        assert [page.get_text().strip() for page in doc] == ["TWO", "ONE"]


# ---------------------------------------------------------------------------
# Lo que debe sobrevivir
# ---------------------------------------------------------------------------


def _rich(path: Path) -> Path:
    with pymupdf.open() as doc:
        for number in range(1, 5):
            page = doc.new_page()
            page.insert_text((50, 50), f"PAGE{number}")
        doc[0].insert_link(
            {
                "kind": pymupdf.LINK_GOTO,
                "from": pymupdf.Rect(50, 100, 150, 120),
                "page": 2,
                "to": pymupdf.Point(0, 0),
            }
        )
        widget = pymupdf.Widget()
        widget.field_name = "keep_field"
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_value = "kept value"
        widget.rect = pymupdf.Rect(50, 200, 250, 230)
        doc[0].add_widget(widget)
        doc.set_toc([[1, "One", 1], [1, "Three", 3]])
        doc.set_metadata({"title": "My title", "author": "Me"})
        doc.save(path)
    return path


def test_reorder_keeps_form_toc_links_and_metadata(tmp_path):
    output = _run(_rich(tmp_path / "rich.pdf"), "3,4,1,2").outputs[0]
    with pymupdf.open(output) as doc:
        assert doc.metadata["title"] == "My title"
        assert doc.get_toc() == [[1, "One", 3], [1, "Three", 1]]
        assert doc[2].first_widget.field_value == "kept value"
        assert [link["page"] for link in doc[2].get_links()] == [0]


def test_removing_pages_keeps_form_toc_links_of_kept_pages(tmp_path):
    output = _run(_rich(tmp_path / "rich.pdf"), "1,3").outputs[0]
    with pymupdf.open(output) as doc:
        assert doc.metadata["title"] == "My title"
        assert doc.get_toc() == [[1, "One", 1], [1, "Three", 2]]
        assert doc[0].first_widget.field_value == "kept value"
        assert [link["page"] for link in doc[0].get_links()] == [1]


def test_duplicating_a_form_page_is_refused_naming_the_page(tmp_path):
    src = _rich(tmp_path / "rich.pdf")
    with pytest.raises(UserError, match="La página 1 tiene campos"):
        _run(src, "1,1")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["rich.pdf"]


def test_duplicate_does_not_copy_resources(tmp_path):
    src = tmp_path / "heavy.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        noise = random.Random(1).randbytes(300 * 300 * 3)
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, 300, 300, noise, 0)
        page.insert_image(page.rect, pixmap=pixmap)
        doc.save(src)
    output = _run(src, "1,1@90,1@180").outputs[0]
    assert output.stat().st_size <= src.stat().st_size * 1.05


def test_reorder_does_not_grow_with_object_streams(tmp_path):
    src = tmp_path / "compact.pdf"
    with pymupdf.open() as doc:
        for number in range(200):
            doc.new_page().insert_text((50, 50), f"page {number}")
        doc.save(src, garbage=3, deflate=True, use_objstms=1)
    output = _run(src, "end-1").outputs[0]
    assert output.stat().st_size <= src.stat().st_size * 1.05


def test_duplicate_with_annotations_gives_each_copy_its_own(tmp_path):
    src = tmp_path / "annotated.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.add_text_annot((50, 50), "note")
        doc.save(src)
    output = _run(src, "1,1").outputs[0]
    with pymupdf.open(output) as doc:
        first = [annot.xref for annot in doc[0].annots()]
        second = [annot.xref for annot in doc[1].annots()]
    assert len(first) == len(second) == 1
    assert first != second


# ---------------------------------------------------------------------------
# Privacidad: lo eliminado no debe quedar en el archivo
# ---------------------------------------------------------------------------


def test_chrome_tagged_pdf_really_loses_deleted_pages(tmp_path):
    src = shutil.copy(CHROME, tmp_path / "chrome.pdf")
    original = _all_decoded(Path(src))
    assert b"Page two" in original and b"Page four" in original
    gone = [_content_of(Path(src), 2), _content_of(Path(src), 4)]
    assert all(content in original for content in gone)
    result = _run(Path(src), "1,3")
    output = result.outputs[0]
    assert _page_objects(output) == 2
    decoded = _all_decoded(output)
    assert b"Page two" not in decoded  # título en el índice
    assert b"Page four" not in decoded
    assert not any(content in decoded for content in gone)
    with pymupdf.open(output) as doc:
        assert "KEEPME-ALPHA" in doc[0].get_text()
        assert "KEEPME-CHARLIE" in doc[1].get_text()
        # Una clave con valor null equivale, en PDF, a no tenerla.
        catalog = doc.pdf_catalog()
        assert doc.xref_get_key(catalog, "StructTreeRoot")[0] == "null"
        assert doc.xref_get_key(catalog, "MarkInfo")[0] == "null"
        assert [entry[1:] for entry in doc.get_toc()] == [
            ["Page one", 1],
            ["Page three", 2],
        ]
        # El enlace a una página conservada sigue funcionando.
        assert [link["page"] for link in doc[0].get_links()] == [1]
    assert result.warnings == [
        "Se quitaron las etiquetas de accesibilidad del resultado."
    ]


def test_chrome_tagged_pdf_reorder_keeps_tags(tmp_path):
    src = shutil.copy(CHROME, tmp_path / "chrome.pdf")
    result = _run(Path(src), "2,1,3,4")
    with pymupdf.open(result.outputs[0]) as doc:
        assert doc.xref_get_key(doc.pdf_catalog(), "StructTreeRoot")[0] == "xref"
    assert result.warnings == []


def test_deleted_form_value_is_gone(tmp_path):
    src = tmp_path / "form.pdf"
    with pymupdf.open() as doc:
        doc.new_page().insert_text((50, 50), "KEEP")
        page = doc.new_page()
        widget = pymupdf.Widget()
        widget.field_name = "SECRETNAME"
        widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
        widget.field_value = "SECRETFIELD"
        widget.rect = pymupdf.Rect(50, 50, 250, 80)
        page.add_widget(widget)
        doc.save(src)
    original = _all_decoded(src)
    assert b"SECRETFIELD" in original and b"SECRETNAME" in original
    output = _run(src, "1").outputs[0]
    decoded = _all_decoded(output)
    assert b"SECRETFIELD" not in decoded
    assert b"SECRETNAME" not in decoded
    assert _page_objects(output) == 1


def _with_name_tree(path: Path) -> Path:
    """PDF con destinos en `/Names/Dests`, como los que generan Word o LaTeX."""
    _pdf(path, pages=3)
    with pymupdf.open(path) as doc:
        kept, gone = doc.page_xref(0), doc.page_xref(1)
        dest = doc.get_new_xref()
        doc.update_object(dest, f"<</D[{gone} 0 R/Fit]>>")
        tree = doc.get_new_xref()
        doc.update_object(
            tree, f"<</Names[(gone) {dest} 0 R (keep) [{kept} 0 R/Fit]]>>"
        )
        names = doc.get_new_xref()
        doc.update_object(names, f"<</Kids[{tree} 0 R]>>")
        doc.xref_set_key(doc.pdf_catalog(), "Names", f"<</Dests {names} 0 R>>")
        path_final = path.with_name(f"{path.stem}_tree.pdf")
        doc.save(path_final)
    return path_final


def test_name_tree_destinations_are_pruned(tmp_path):
    src = _with_name_tree(tmp_path / "names.pdf")
    assert _page_objects(src) == 3
    gone = _content_of(src, 2)
    assert gone in _all_decoded(src)
    output = _run(src, "1,3").outputs[0]
    assert _page_objects(output) == 2
    decoded = _all_decoded(output)
    assert gone not in decoded
    with pymupdf.open(output) as doc:
        assert doc.resolve_names().keys() == {"keep"}


@pytest.mark.parametrize("indirect", [True, False])
def test_dests_dictionary_is_pruned(tmp_path, indirect):
    src = _pdf(tmp_path / "a.pdf", pages=3)
    final = tmp_path / "dests.pdf"
    with pymupdf.open(src) as doc:
        kept, gone = doc.page_xref(0), doc.page_xref(1)
        indirect_dest = doc.get_new_xref()
        doc.update_object(indirect_dest, f"[{gone} 0 R/Fit]")
        dests = (
            f"<</keep[{kept} 0 R/Fit]/with#20space[{kept} 0 R/Fit]/gone[{gone} 0 R/Fit]"
            f"/viaobject {indirect_dest} 0 R/viadict<</D[{gone} 0 R/Fit]>>>>"
        )
        if indirect:
            holder = doc.get_new_xref()
            doc.update_object(holder, dests)
            dests = f"{holder} 0 R"
        doc.xref_set_key(doc.pdf_catalog(), "Dests", dests)
        doc.save(final)
    assert _page_objects(final) == 3
    gone_content = _content_of(final, 2)
    output = _run(final, "1,3").outputs[0]
    assert _page_objects(output) == 2
    assert gone_content not in _all_decoded(output)
    assert b"gone" not in _all_decoded(output)
    with pymupdf.open(output) as doc:
        assert doc.resolve_names().keys() == {"keep", "with space"}


def test_toc_children_of_a_deleted_entry_are_promoted(tmp_path):
    src = _pdf(tmp_path / "a.pdf", pages=3)
    with pymupdf.open(src) as doc:
        doc.set_toc([[1, "Gone", 1], [2, "Child", 2], [1, "Last", 3]])
        doc.saveIncr()
    output = _run(src, "2,3").outputs[0]
    with pymupdf.open(output) as doc:
        assert doc.get_toc() == [[1, "Child", 1], [1, "Last", 2]]
    assert b"Gone" not in _all_decoded(output)
    assert b"Child" in _all_decoded(output)


def test_toc_entries_without_a_page_survive(tmp_path):
    """Un marcador a una web tampoco tiene página, pero no se eliminó nada de él."""
    src = _pdf(tmp_path / "a.pdf", pages=2)
    with pymupdf.open(src) as doc:
        doc.set_toc(
            [
                [1, "Page", 1],
                [1, "Site", -1, {"kind": pymupdf.LINK_URI, "uri": "https://a.test"}],
            ]
        )
        doc.saveIncr()
    with pymupdf.open(_run(src, "1").outputs[0]) as doc:
        assert [entry[1] for entry in doc.get_toc()] == ["Page", "Site"]


# ---------------------------------------------------------------------------
# Invariante: nunca se publica un archivo con páginas huérfanas
# ---------------------------------------------------------------------------


def _pretend_pruning_failed(monkeypatch):
    """La edición normal deja huérfanas; el respaldo por tramos parte de otro doc."""
    real = logic._page_objects

    def fake(doc):
        fake.calls += 1
        return real(doc) + (1 if fake.calls == 1 else 0)

    fake.calls = 0
    monkeypatch.setattr(logic, "_page_objects", fake)


def test_fallback_rebuilds_and_warns_when_invariant_fails(tmp_path, monkeypatch):
    src = _pdf(tmp_path / "a.pdf")
    _pretend_pruning_failed(monkeypatch)
    result = _run(src, "3@90,1,1")
    assert _texts(result.outputs[0]) == ["TEXT-0003.", "TEXT-0001.", "TEXT-0001."]
    with pymupdf.open(result.outputs[0]) as doc:
        assert [page.rotation for page in doc] == [90, 0, 0]
    assert any("reconstruyó" in w for w in result.warnings)


def test_reference_the_pruning_does_not_know_triggers_the_fallback(tmp_path):
    """Sin simular nada: `/OpenAction` mantiene viva una página eliminada."""
    src = _pdf(tmp_path / "a.pdf", pages=3)
    final = tmp_path / "open_action.pdf"
    with pymupdf.open(src) as doc:
        gone = doc.page_xref(1)
        doc.xref_set_key(doc.pdf_catalog(), "OpenAction", f"[{gone} 0 R/Fit]")
        doc.save(final)
    gone_content = _content_of(final, 2)
    result = _run(final, "1,3")
    assert any("reconstruyó" in w for w in result.warnings)
    assert _page_objects(result.outputs[0]) == 2
    assert gone_content not in _all_decoded(result.outputs[0])


def test_fallback_does_not_inflate_shared_resources(tmp_path, monkeypatch):
    src = tmp_path / "shared.pdf"
    noise = random.Random(1).randbytes(200 * 200 * 3)
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, 200, 200, noise, 0)
    with pymupdf.open() as doc:
        image = 0
        for number in range(40):
            page = doc.new_page()
            image = page.insert_image(
                pymupdf.Rect(0, 0, 100, 100), pixmap=pixmap, xref=image
            )
            page.insert_text((50, 200), f"page {number}")
        doc.save(src, garbage=3, deflate=True)
    plan = [(page, 0) for page in range(1, 41)]
    random.Random(2).shuffle(plan)
    _pretend_pruning_failed(monkeypatch)
    result = _run(src, serialize_plan(plan))
    assert any("reconstruyó" in w for w in result.warnings)
    assert result.outputs[0].stat().st_size <= src.stat().st_size * 1.2


def test_nothing_is_published_if_fallback_also_fails(tmp_path, monkeypatch):
    src = _pdf(tmp_path / "a.pdf")
    monkeypatch.setattr(logic, "_page_objects", lambda _doc: 999)
    with pytest.raises(UserError, match="no se guardó nada"):
        _run(src, "1")
    assert [p.name for p in tmp_path.iterdir()] == ["a.pdf"]
