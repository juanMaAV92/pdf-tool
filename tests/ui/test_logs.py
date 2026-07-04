from pathlib import Path

import pdftool.ui.logs as logs_mod
from pdftool.ui.logs import download_log_button, make_log_picker


class _FakeSaveEvent:
    def __init__(self, path):
        self.path = path


def test_button_builds():
    picker = make_log_picker()
    btn = download_log_button(picker)
    assert btn is not None


def test_save_writes_log_content(tmp_path, monkeypatch):
    log_file = tmp_path / "pdf-tool.log"
    log_file.write_text("linea 1\n", encoding="utf-8")
    monkeypatch.setattr(logs_mod, "log_paths", lambda: [log_file])
    picker = make_log_picker()
    target = tmp_path / "salida.txt"
    picker.on_result(_FakeSaveEvent(str(target)))
    assert target.read_text(encoding="utf-8") == "linea 1\n"


def test_save_concatenates_backup_first(tmp_path, monkeypatch):
    backup = tmp_path / "pdf-tool.log.1"
    current = tmp_path / "pdf-tool.log"
    backup.write_text("viejo\n", encoding="utf-8")
    current.write_text("nuevo\n", encoding="utf-8")
    monkeypatch.setattr(logs_mod, "log_paths", lambda: [backup, current])
    picker = make_log_picker()
    target = tmp_path / "salida.txt"
    picker.on_result(_FakeSaveEvent(str(target)))
    assert target.read_text(encoding="utf-8") == "viejo\nnuevo\n"


def test_save_adds_txt_suffix_and_handles_empty_log(tmp_path, monkeypatch):
    monkeypatch.setattr(logs_mod, "log_paths", lambda: [])
    picker = make_log_picker()
    picker.on_result(_FakeSaveEvent(str(tmp_path / "salida")))
    out = tmp_path / "salida.txt"
    assert "registro vacío" in out.read_text(encoding="utf-8")


def test_cancel_does_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(logs_mod, "log_paths", lambda: [])
    picker = make_log_picker()
    picker.on_result(_FakeSaveEvent(None))  # cancelado: no explota, no escribe
    assert list(tmp_path.iterdir()) == []
