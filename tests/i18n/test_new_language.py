"""Añadir un idioma es añadir un diccionario: sin cambiar código."""

import io
import json
import shutil
from contextlib import redirect_stdout
from types import SimpleNamespace

from pdftool import i18n
from pdftool.cli import main


def _with_xx(tmp_path):
    for path in i18n.LOCALES_DIR.glob("*.json"):
        shutil.copy2(path, tmp_path / path.name)
    data = json.loads((tmp_path / "en.json").read_text(encoding="utf-8"))
    data["_meta"]["name"] = "Xx"
    data["tool.merge.name"] = "Xx Merge"
    (tmp_path / "xx.json").write_text(json.dumps(data), encoding="utf-8")
    i18n.use_locales_dir(tmp_path)


def test_complete_new_language_needs_no_code(tmp_path):
    _with_xx(tmp_path)
    assert ("xx", "Xx") in i18n.available_languages()

    out = io.StringIO()
    with redirect_stdout(out):
        assert main(["--lang", "xx", "list"], env={}) == 0
    assert "Xx Merge" in out.getvalue()


def test_new_language_appears_in_the_app_dialog(tmp_path, monkeypatch):
    import flet as ft

    from pdftool.core.config import Settings
    from pdftool.ui import app

    _with_xx(tmp_path)
    page = SimpleNamespace(close=lambda c: None)
    dialog = app._language_dialog(page, Settings(), lambda code: None)
    labels = [r.label for r in dialog.content.content.controls]
    assert "Xx" in labels
    assert isinstance(dialog, ft.AlertDialog)


def test_incomplete_new_language_falls_back_to_english(tmp_path):
    for path in i18n.LOCALES_DIR.glob("*.json"):
        shutil.copy2(path, tmp_path / path.name)
    (tmp_path / "yy.json").write_text(
        json.dumps({"_meta": {"name": "Yy"}, "ui.home.title": "Yy tools"}),
        encoding="utf-8",
    )
    i18n.use_locales_dir(tmp_path)
    i18n.set_language("yy")
    assert i18n.t("ui.home.title") == "Yy tools"
    assert i18n.t("tool.merge.name") == "Merge PDFs"
