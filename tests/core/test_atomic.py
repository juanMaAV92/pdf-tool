from pathlib import Path

import pytest

from pdftool.core.atomic import atomic_copy, atomic_output


def _temporary_files(path: Path) -> list[Path]:
    return list(path.parent.glob(".pdf-tool-*"))


def test_atomic_output_publishes_only_after_success(tmp_path):
    target = tmp_path / "resultado.pdf"

    with atomic_output(target) as temporary:
        temporary.write_bytes(b"completo")
        assert not target.exists()

    assert target.read_bytes() == b"completo"
    assert _temporary_files(target) == []


def test_atomic_output_keeps_previous_target_on_failure(tmp_path):
    target = tmp_path / "resultado.pdf"
    target.write_bytes(b"anterior")

    with pytest.raises(RuntimeError):
        with atomic_output(target) as temporary:
            temporary.write_bytes(b"incompleto")
            raise RuntimeError("fallo de escritura")

    assert target.read_bytes() == b"anterior"
    assert _temporary_files(target) == []


def test_atomic_copy_publishes_complete_copy(tmp_path):
    source = tmp_path / "origen.pdf"
    target = tmp_path / "copia.pdf"
    source.write_bytes(b"contenido")

    atomic_copy(source, target)

    assert target.read_bytes() == source.read_bytes()
    assert _temporary_files(target) == []
