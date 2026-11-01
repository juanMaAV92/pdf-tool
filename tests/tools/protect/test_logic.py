from pathlib import Path

import pymupdf
import pytest
from pydantic import ValidationError

from pdftool.tools.protect.logic import protect
from pdftool.tools.protect.params import ProtectParams


def _pdf(path: Path) -> Path:
    with pymupdf.open() as d:
        d.new_page().insert_text((72, 72), "Hola")
        d.save(str(path))
    return path


def _protected_pdf(path: Path, pw: str = "clave") -> Path:
    with pymupdf.open() as d:
        d.new_page().insert_text((72, 72), "Secreto")
        d.save(
            str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=pw, user_pw=pw
        )
    return path


def test_empty_password_rejected():
    with pytest.raises(ValidationError):
        ProtectParams(mode="protect", password="")


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        ProtectParams(mode="otro", password="x")


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        protect([Path("/no/such.pdf")], ProtectParams(mode="protect", password="x"))


def test_empty_inputs_raises():
    with pytest.raises(ValueError):
        protect([], ProtectParams(mode="protect", password="x"))


def test_protect_makes_pdf_need_password(tmp_path):
    plain = _pdf(tmp_path / "doc.pdf")
    out = protect([plain], ProtectParams(mode="protect", password="clave")).outputs[0]
    assert out.exists()
    d = pymupdf.open(str(out))
    try:
        assert d.needs_pass
        assert d.authenticate("clave")
    finally:
        d.close()


def test_remove_clears_password(tmp_path):
    prot = _protected_pdf(tmp_path / "sec.pdf", pw="clave")
    out = protect([prot], ProtectParams(mode="remove", password="clave")).outputs[0]
    assert out.exists()
    d = pymupdf.open(str(out))
    try:
        assert not d.needs_pass
    finally:
        d.close()


def test_remove_wrong_password_raises(tmp_path):
    prot = _protected_pdf(tmp_path / "sec.pdf", pw="clave")
    with pytest.raises(ValueError):
        protect([prot], ProtectParams(mode="remove", password="incorrecta"))


def test_progress_reaches_one(tmp_path):
    plain = _pdf(tmp_path / "doc.pdf")
    seen = []
    protect(
        [plain],
        ProtectParams(mode="protect", password="x"),
        progress=lambda p, m: seen.append(p),
    )
    assert seen and seen[-1] == 1.0


def test_protect_multiple_pdfs(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    b = _pdf(tmp_path / "b.pdf")
    res = protect([a, b], ProtectParams(mode="protect", password="clave"))
    assert len(res.outputs) == 2
    assert res.summary == "2 PDFs protegidos"
    assert [item.message for item in res.items] == [
        "→ a_protegido.pdf",
        "→ b_protegido.pdf",
    ]
    assert all(item.ok for item in res.items)
    for out in res.outputs:
        d = pymupdf.open(str(out))
        try:
            assert d.needs_pass
            assert d.authenticate("clave")
        finally:
            d.close()


def test_remove_multiple_pdfs(tmp_path):
    a = _protected_pdf(tmp_path / "a.pdf", pw="clave")
    b = _protected_pdf(tmp_path / "b.pdf", pw="clave")
    res = protect([a, b], ProtectParams(mode="remove", password="clave"))
    assert len(res.outputs) == 2
    assert res.summary == "2 contraseñas removidas"
    for out in res.outputs:
        d = pymupdf.open(str(out))
        try:
            assert not d.needs_pass
        finally:
            d.close()


def test_mixed_batch_continues_and_reports(tmp_path):
    ok = _protected_pdf(tmp_path / "ok.pdf", pw="clave")
    bad = _protected_pdf(tmp_path / "bad.pdf", pw="otra")
    res = protect([ok, bad], ProtectParams(mode="remove", password="clave"))
    assert len(res.outputs) == 1
    assert res.outputs[0].name == "ok_sin_clave.pdf"
    assert res.summary == "1 de 2 PDFs procesados"
    assert res.items[0].message == "→ ok_sin_clave.pdf"
    assert "Contraseña incorrecta" in res.items[1].message
    assert res.items[1].ok is False


def test_all_fail_raises(tmp_path):
    a = _protected_pdf(tmp_path / "a.pdf", pw="otra")
    b = _protected_pdf(tmp_path / "b.pdf", pw="otra")
    with pytest.raises(ValueError):
        protect([a, b], ProtectParams(mode="remove", password="clave"))


def test_single_file_has_no_items(tmp_path):
    plain = _pdf(tmp_path / "doc.pdf")
    res = protect([plain], ProtectParams(mode="protect", password="x"))
    assert res.items is None
    assert res.summary.startswith("PDF protegido → ")


def test_multi_progress_labels_and_completion(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    b = _pdf(tmp_path / "b.pdf")
    seen = []
    protect(
        [a, b],
        ProtectParams(mode="protect", password="x"),
        progress=lambda p, m: seen.append((p, m)),
    )
    assert seen[-1][0] == 1.0
    assert any(m.startswith("[1/2] a.pdf:") for _p, m in seen)
    assert any(m.startswith("[2/2] b.pdf:") for _p, m in seen)


def test_protect_does_not_overwrite_a_previous_output(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    (tmp_path / "a_protegido.pdf").write_bytes(b"previo")

    res = protect([a], ProtectParams(mode="protect", password="clave"))

    assert res.outputs[0] == tmp_path / "a_protegido (1).pdf"
    assert (tmp_path / "a_protegido.pdf").read_bytes() == b"previo"


def test_remove_password_does_not_overwrite_a_previous_output(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    protected = tmp_path / "a_protegido.pdf"
    with pymupdf.open(str(a)) as doc:
        doc.save(
            str(protected),
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="clave",
            user_pw="clave",
        )
    (tmp_path / "a_protegido_sin_clave.pdf").write_bytes(b"previo")

    res = protect([protected], ProtectParams(mode="remove", password="clave"))

    assert res.outputs[0] == tmp_path / "a_protegido_sin_clave (1).pdf"
    assert (tmp_path / "a_protegido_sin_clave.pdf").read_bytes() == b"previo"


def test_protect_writes_to_output_dir(tmp_path):
    destino = tmp_path / "destino"
    destino.mkdir()
    a = _pdf(tmp_path / "a.pdf")

    res = protect(
        [a], ProtectParams(mode="protect", password="clave", output_dir=destino)
    )

    assert res.outputs[0] == destino / "a_protegido.pdf"
    assert res.outputs[0].exists()


def test_cancellation_stops_the_batch(tmp_path):
    from pdftool.core.jobs import JobCancelled

    a = _pdf(tmp_path / "a.pdf")
    b = _pdf(tmp_path / "b.pdf")
    calls = []

    def cancel(p, m):
        calls.append(m)
        raise JobCancelled()

    with pytest.raises(JobCancelled):
        protect([a, b], ProtectParams(mode="protect", password="x"), progress=cancel)
    assert len(calls) == 1


# Un PDF al que se le quitó la contraseña puede conservar el diccionario de
# cifrado viejo como objeto suelto, con los hashes (/O, /U) de esa contraseña.
STALE_ENCRYPT = "<</Filter/Standard/V 2/R 3/Length 128/P -1836/O<{h}>/U<{h}>>>"


def _pdf_with_stale_encryption(path: Path) -> Path:
    with pymupdf.open() as d:
        d.new_page().insert_text((72, 72), "Hola")
        xref = d.get_new_xref()
        d.update_object(xref, STALE_ENCRYPT.format(h="AB" * 32))
        d.save(str(path))
    assert path.read_bytes().count(b"/Filter/Standard") == 1
    return path


def test_remove_drops_stale_encryption_objects(tmp_path):
    src = _pdf_with_stale_encryption(tmp_path / "a.pdf")
    res = protect([src], ProtectParams(mode="remove", password="x"))
    assert b"/Filter/Standard" not in res.outputs[0].read_bytes()


def test_protect_keeps_only_the_new_encryption(tmp_path):
    src = _pdf_with_stale_encryption(tmp_path / "a.pdf")
    res = protect([src], ProtectParams(mode="protect", password="nueva"))
    data = res.outputs[0].read_bytes()
    assert data.count(b"/Filter/Standard") == 1
    assert b"/V 2" not in data
    with pymupdf.open(str(res.outputs[0])) as d:
        assert d.needs_pass and d.authenticate("nueva")
        assert "Hola" in d[0].get_text()


def test_protect_suffixes_follow_language(tmp_path):
    from pdftool import i18n

    i18n.set_language("en")
    src = _pdf(tmp_path / "doc.pdf")
    result = protect([src], ProtectParams(password="x"))
    assert result.outputs[0].name == "doc_protected.pdf"
    assert result.summary == "PDF protected → doc_protected.pdf"
    removed = protect(result.outputs, ProtectParams(mode="remove", password="x"))
    assert removed.outputs[0].name == "doc_protected_unlocked.pdf"
    assert removed.summary == "Password removed → doc_protected_unlocked.pdf"


def test_protect_batch_summaries_in_english(tmp_path):
    from pdftool import i18n

    i18n.set_language("en")
    a, b = _pdf(tmp_path / "a.pdf"), _pdf(tmp_path / "b.pdf")
    result = protect([a, b], ProtectParams(password="x"))
    assert result.summary == "2 PDFs protected"
    locked = _protected_pdf(tmp_path / "c.pdf")
    result = protect([a, locked], ProtectParams(password="x"))
    assert result.summary == "1 of 2 PDFs processed"
