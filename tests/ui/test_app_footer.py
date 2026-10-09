import flet as ft

from pdftool import __version__
from pdftool.ui.app import _build_footer


def test_footer_keeps_utilities_in_named_menu_and_version_visible():
    called = []
    footer = _build_footer(
        "Cambiar a tema claro",
        lambda _: called.append("theme"),
        lambda _: called.append("log"),
        lambda _: called.append("author"),
    )
    version, menu = footer.controls
    assert version.value == f"v{__version__}"
    assert isinstance(menu, ft.PopupMenuButton)
    assert menu.content.semantics_label == "Opciones de la aplicación"
    assert [item.text for item in menu.items] == [
        "Cambiar a tema claro",
        "Descargar log",
        "Acerca del autor",
    ]
    for item in menu.items:
        item.on_click(None)
    assert called == ["theme", "log", "author"]
