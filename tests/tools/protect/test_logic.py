from pathlib import Path

import fitz
import pytest
from pydantic import ValidationError

from pdftool.tools.protect.logic import protect
from pdftool.tools.protect.params import ProtectParams


def _pdf(path: Path) -> Path:
    with fitz.open() as d:
        d.new_page().insert_text((72, 72), "Hola")
        d.save(str(path))
    return path


def _protected_pdf(path: Path, pw: str = "clave") -> Path:
    with fitz.open() as d:
        d.new_page().insert_text((72, 72), "Secreto")
        d.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256,
               owner_pw=pw, user_pw=pw)
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
    d = fitz.open(str(out))
    try:
        assert d.needs_pass
        assert d.authenticate("clave")
    finally:
        d.close()


def test_remove_clears_password(tmp_path):
    prot = _protected_pdf(tmp_path / "sec.pdf", pw="clave")
    out = protect([prot], ProtectParams(mode="remove", password="clave")).outputs[0]
    assert out.exists()
    d = fitz.open(str(out))
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
    protect([plain], ProtectParams(mode="protect", password="x"),
            progress=lambda p, m: seen.append(p))
    assert seen and seen[-1] == 1.0


def test_protect_multiple_pdfs(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    b = _pdf(tmp_path / "b.pdf")
    res = protect([a, b], ProtectParams(mode="protect", password="clave"))
    assert len(res.outputs) == 2
    assert res.summary == "2 PDFs protegidos"
    assert res.details == ["→ a_protegido.pdf", "→ b_protegido.pdf"]
    for out in res.outputs:
        d = fitz.open(str(out))
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
        d = fitz.open(str(out))
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
    assert res.details[0] == "→ ok_sin_clave.pdf"
    assert "Contraseña incorrecta" in res.details[1]


def test_all_fail_raises(tmp_path):
    a = _protected_pdf(tmp_path / "a.pdf", pw="otra")
    b = _protected_pdf(tmp_path / "b.pdf", pw="otra")
    with pytest.raises(ValueError):
        protect([a, b], ProtectParams(mode="remove", password="clave"))


def test_single_file_has_no_details(tmp_path):
    plain = _pdf(tmp_path / "doc.pdf")
    res = protect([plain], ProtectParams(mode="protect", password="x"))
    assert res.details is None
    assert res.summary.startswith("PDF protegido → ")


def test_multi_progress_labels_and_completion(tmp_path):
    a = _pdf(tmp_path / "a.pdf")
    b = _pdf(tmp_path / "b.pdf")
    seen = []
    protect([a, b], ProtectParams(mode="protect", password="x"),
            progress=lambda p, m: seen.append((p, m)))
    assert seen[-1][0] == 1.0
    assert any(m.startswith("[1/2] a.pdf:") for _p, m in seen)
    assert any(m.startswith("[2/2] b.pdf:") for _p, m in seen)
