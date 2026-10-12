import flet as ft

from pdftool import __version__
from pdftool.ui.app import _build_footer


def _footer(called):
    return _build_footer(
        "Cambiar a tema claro",
        lambda _: called.append("theme"),
        lambda _: called.append("log"),
        lambda _: called.append("author"),
    )


def test_author_credit_is_visible_in_the_footer():
    """La firma del autor se ve sin abrir menús, discreta y con enlace."""
    called = []
    footer, _theme_item = _footer(called)
    credit = footer.controls[0]

    assert isinstance(credit, ft.TextButton)
    assert credit.text == "Hecho por @juanmaav92"
    assert credit.tooltip == "Visitar el sitio del autor"
    credit.on_click(None)
    assert called == ["author"]


def test_footer_keeps_utilities_in_named_menu_and_version_visible():
    called = []
    footer, theme_item = _footer(called)
    _credit, _spacer, version, menu = footer.controls
    assert theme_item is menu.items[0]
    assert version.value == f"v{__version__}"
    assert isinstance(menu, ft.PopupMenuButton)
    assert menu.content.semantics_label == "Opciones de la aplicación"
    assert [item.text for item in menu.items] == [
        "Cambiar a tema claro",
        "Guardar informe de diagnóstico",
    ]
    for item in menu.items:
        item.on_click(None)
    assert called == ["theme", "log"]


def test_theme_label_says_current_and_next_mode():
    from pdftool.ui.app import _theme_label

    assert _theme_label("system") == "Tema: Sistema · cambiar a Claro"
    assert _theme_label("dark") == "Tema: Oscuro · cambiar a Sistema"


def test_window_has_a_minimum_size():
    from types import SimpleNamespace

    from pdftool.ui.app import _configure_window

    page = SimpleNamespace(window=SimpleNamespace())
    _configure_window(page)
    assert page.window.min_width == 820
    assert page.window.min_height == 560
    assert (page.window.width, page.window.height) == (980, 680)


def test_shutdown_hooks_run_on_the_event_loop():
    """Flet manda los manejadores síncronos a su pool de hilos, que al cerrar
    la ventana ya está apagado («cannot schedule new futures after shutdown»).
    Los de cierre deben ser corrutinas para ejecutarse en el propio bucle."""
    import asyncio
    import inspect
    from types import SimpleNamespace

    from pdftool.ui.app import _install_shutdown_hooks

    calls = []
    page = SimpleNamespace(on_close=None, on_disconnect=None)
    _install_shutdown_hooks(page, lambda: calls.append(1))

    assert inspect.iscoroutinefunction(page.on_close)
    assert inspect.iscoroutinefunction(page.on_disconnect)
    asyncio.run(page.on_close(None))
    asyncio.run(page.on_disconnect(None))
    assert calls == [1, 1]
