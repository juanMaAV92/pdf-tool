import flet as ft

from pdftool import __version__
from pdftool.ui.app import _build_footer


def test_footer_keeps_utilities_in_named_menu_and_version_visible():
    called = []
    footer, theme_item = _build_footer(
        "Cambiar a tema claro",
        lambda _: called.append("theme"),
        lambda _: called.append("log"),
        lambda _: called.append("author"),
    )
    version, menu = footer.controls
    assert theme_item is menu.items[0]
    assert version.value == f"v{__version__}"
    assert isinstance(menu, ft.PopupMenuButton)
    assert menu.content.semantics_label == "Opciones de la aplicación"
    assert [item.text for item in menu.items] == [
        "Cambiar a tema claro",
        "Guardar informe de diagnóstico",
        "Acerca del autor",
    ]
    for item in menu.items:
        item.on_click(None)
    assert called == ["theme", "log", "author"]


def test_theme_label_says_current_and_next_mode():
    from pdftool.ui.app import _theme_label

    assert _theme_label("system") == "Tema: Sistema · cambiar a Claro"
    assert _theme_label("dark") == "Tema: Oscuro · cambiar a Sistema"


def test_window_has_a_minimum_size():
    from types import SimpleNamespace

    from pdftool.ui.app import _configure_window

    page = SimpleNamespace(window=SimpleNamespace())
    _configure_window(page)
    assert page.window.min_width == 760
    assert page.window.min_height == 560
    assert (page.window.width, page.window.height) == (980, 680)
