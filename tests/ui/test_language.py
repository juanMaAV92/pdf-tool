"""Idioma de la app: ajuste guardado, selector en el menú y cambio al momento."""

import json
from types import SimpleNamespace

import flet as ft
import pytest

from pdftool import i18n
from pdftool.core.config import Settings, load_settings
from pdftool.ui import app


class _FakePage:
    """Lo justo de ft.Page para montar la app completa en un test."""

    def __init__(self) -> None:
        self.controls: list = []
        self.overlay: list = []
        self.opened: list = []
        self.window = SimpleNamespace()
        self.title = ""

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        pass

    def open(self, control) -> None:
        self.opened.append(control)

    def close(self, control) -> None:
        pass

    def launch_url(self, url) -> None:
        self.launched = url


@pytest.fixture
def mounted(monkeypatch, tmp_path):
    saved: list[Settings] = []
    settings = Settings()
    monkeypatch.setattr(app, "load_settings", lambda: settings)
    monkeypatch.setattr(app, "save_settings", lambda s: saved.append(s.model_copy()))
    monkeypatch.setattr(app, "_start_update_check", lambda *a, **k: None)
    page = _FakePage()
    app.build_app(page)
    return SimpleNamespace(page=page, settings=settings, saved=saved)


def _texts(control) -> list[str]:
    found: list[str] = []

    def walk(c):
        if isinstance(c, ft.Text) and isinstance(c.value, str):
            found.append(c.value)
        for attr in ("controls", "content"):
            child = getattr(c, attr, None)
            if isinstance(child, list):
                for x in child:
                    walk(x)
            elif child is not None:
                walk(child)

    walk(control)
    return found


def _menu(page):
    footer = page.controls[0].controls[-1]
    return footer.controls[-1]


def _language_item(page):
    return next(i for i in _menu(page).items if i.data == "language")


def test_settings_language_defaults_to_system():
    assert Settings().language == "system"


def test_unknown_language_in_settings_opens_in_system_language(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": 42, "theme_mode": "dark"}), "utf-8")
    loaded = load_settings(path)
    assert loaded.language == "system"
    assert loaded.theme_mode == "dark"
    # Un código que ya no tiene diccionario cae al idioma del sistema (es).
    assert i18n.resolve_language("pt") == "es"


def test_menu_shows_language_entry_with_current_name(mounted):
    assert _language_item(mounted.page).text == "Idioma: Español"


def test_dialog_lists_system_and_available_languages(mounted):
    _language_item(mounted.page).on_click(None)
    dialog = mounted.page.opened[-1]
    assert isinstance(dialog, ft.AlertDialog)
    labels = [r.label for r in dialog.content.content.controls]
    assert labels[0] == "Idioma del sistema"
    assert "English" in labels and "Español" in labels


def test_choosing_language_saves_and_rebuilds(mounted):
    overlay_before = len(mounted.page.overlay)
    app.choose_language(mounted.page, mounted.settings, "en")
    assert mounted.settings.language == "en"
    assert mounted.saved[-1].language == "en"
    assert i18n.current_language() == "en"
    texts = _texts(mounted.page.controls[0])
    assert "PDF tools" in texts
    assert "Herramientas PDF" not in texts
    assert len(mounted.page.overlay) == overlay_before
    assert _language_item(mounted.page).text == "Language: English"


def test_language_entry_disabled_while_running(mounted):
    tools = app.current_tools(mounted.page)
    tools[0]._running = True
    app.refresh_language_item(mounted.page)
    item = _language_item(mounted.page)
    assert item.disabled
    tools[0]._running = False
    app.refresh_language_item(mounted.page)
    assert not _language_item(mounted.page).disabled


def test_footer_links_to_the_pdf_tool_page(mounted):
    credit = mounted.page.controls[0].controls[-1].controls[0]
    assert credit.text == "Powered by @juanmaav92"
    credit.on_click(None)
    assert mounted.page.launched == "https://juanmaav92.github.io/pdf-tool"


def test_watermark_colors_use_ids():
    from pdftool.tools.watermark.panel import WatermarkTool as WatermarkPanel

    panel = WatermarkPanel()
    page = SimpleNamespace(overlay=[], update=lambda: None, open=lambda c: None)
    from pdftool.core.plugin import ToolContext

    panel.build_panel(ToolContext(page=page, run_job=lambda **k: None))
    dd = panel._color_dd
    assert dd.value == "gray"
    assert {o.key: o.text for o in dd.options}["gray"] == "Gris"
    i18n.set_language("en")
    panel2 = WatermarkPanel()
    panel2.build_panel(ToolContext(page=page, run_job=lambda **k: None))
    assert {o.key: o.text for o in panel2._color_dd.options}["gray"] == "Gray"


def test_opening_the_menu_refreshes_the_language_entry(mounted):
    tools = app.current_tools(mounted.page)
    tools[1]._running = True
    _menu(mounted.page).on_open(None)
    assert _language_item(mounted.page).disabled
    _language_item(mounted.page).on_click(None)
    assert not any(isinstance(c, ft.AlertDialog) for c in mounted.page.opened)
