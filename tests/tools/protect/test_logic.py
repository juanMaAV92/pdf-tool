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
