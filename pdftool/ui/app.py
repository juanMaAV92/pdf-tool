from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from pdftool import __version__
from pdftool.core import registry
from pdftool.core.config import load_settings, save_settings
from pdftool.core.jobs import run_job, shutdown_job_executor
from pdftool.core.plugin import ToolContext
from pdftool.core.updater import GITHUB_REPO, check_for_update
from pdftool.ui.accessibility import icon_content
from pdftool.ui.logs import LOG_LABEL, download_log_button, make_log_picker
from pdftool.ui.theme import build_theme, next_mode, resolve_mode
from pdftool.ui.thumbnails import shutdown_thumbnail_executor

AUTHOR_NAME = "Juan Manuel Armero"
AUTHOR_SITE = "https://juanMaAV92.github.io"


def _build_footer(theme_label, on_theme, on_log, on_author):
    """Pie: firma del autor a la izquierda; versión y utilidades a la derecha.

    Devuelve (pie, ítem del tema): el ítem se reetiqueta al cambiar el tema.
    """
    theme_item = ft.PopupMenuItem(
        text=theme_label, icon=ft.Icons.BRIGHTNESS_6, on_click=on_theme
    )
    # Visible en todas las pantallas pero discreta: mismo tono apagado y
    # tamaño que la versión, sin competir con el resultado del panel.
    credit = ft.TextButton(
        f"Hecho por {AUTHOR_NAME}",
        icon=ft.Icons.OPEN_IN_NEW,
        tooltip="Visitar el sitio del autor",
        on_click=on_author,
        style=ft.ButtonStyle(
            color=ft.Colors.ON_SURFACE_VARIANT,
            icon_size=14,
            text_style=ft.TextStyle(size=12),
            padding=ft.padding.symmetric(horizontal=8, vertical=4),
        ),
    )
    footer = ft.Row(
        [
            credit,
            ft.Container(expand=True),
            ft.Text(
                f"v{__version__}",
                size=11,
                color=ft.Colors.ON_SURFACE_VARIANT,
                tooltip=f"Versión de la aplicación: {__version__}",
            ),
            ft.PopupMenuButton(
                content=icon_content(ft.Icons.MORE_HORIZ, "Opciones de la aplicación"),
                tooltip="Opciones de la aplicación",
                items=[
                    theme_item,
                    ft.PopupMenuItem(
                        text=LOG_LABEL, icon=ft.Icons.DOWNLOAD, on_click=on_log
                    ),
                ],
            ),
        ],
    )
    return footer, theme_item


def _tool_card(index, tool, on_open):
    return ft.OutlinedButton(
        content=ft.Column(
            [
                # La categoría va en la esquina, en la misma línea que el icono:
                # agrupa sin añadir altura (la barra lateral ya muestra grupos).
                ft.Row(
                    [
                        ft.Icon(tool.meta.icon, size=30),
                        ft.Text(
                            tool.meta.category,
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Text(tool.meta.name, weight=ft.FontWeight.BOLD, size=15),
                ft.Text(
                    tool.meta.description, size=12, color=ft.Colors.ON_SURFACE_VARIANT
                ),
            ],
            spacing=6,
            tight=True,
            width=208,
            height=108,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        width=240,
        height=140,
        style=ft.ButtonStyle(
            padding=16,
            alignment=ft.alignment.top_left,
            color=ft.Colors.ON_SURFACE,
            shape=ft.RoundedRectangleBorder(radius=14),
            side={
                ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
                ft.ControlState.FOCUSED: ft.BorderSide(2, ft.Colors.PRIMARY),
            },
            bgcolor={ft.ControlState.FOCUSED: ft.Colors.PRIMARY_CONTAINER},
        ),
        on_click=lambda _e: on_open(index),
    )


def _group_by_category(tools):
    """[(categoría, [(índice, herramienta), …]), …] respetando el orden de
    `tools` (ya ordenadas por `meta.order`); cada categoría aparece donde lo
    hace su primera herramienta."""
    groups: dict[str, list] = {}
    for index, tool in enumerate(tools):
        groups.setdefault(tool.meta.category, []).append((index, tool))
    return list(groups.items())


def _build_home(tools, on_open):
    # Una sola cuadrícula que se ajusta al ancho: las herramientas ya llegan
    # ordenadas por tarea, así que las de una misma categoría quedan juntas.
    # (Una fila por categoría dejaba la pantalla medio vacía y forzaba scroll.)
    cards = ft.Row(
        [_tool_card(i, t, on_open) for i, t in enumerate(tools)],
        wrap=True,
        spacing=16,
        run_spacing=16,
    )
    return ft.Column(
        [
            ft.Text("Herramientas PDF", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Elige una herramienta para empezar."),
            ft.Container(height=8),
            cards,
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _nav_style(selected: bool) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        bgcolor=ft.Colors.SECONDARY_CONTAINER if selected else None,
        color=ft.Colors.ON_SECONDARY_CONTAINER if selected else ft.Colors.ON_SURFACE,
        alignment=ft.alignment.center_left,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
        shape=ft.RoundedRectangleBorder(radius=10),
    )


def _nav_button(icon, label: str, on_click) -> ft.TextButton:
    return ft.TextButton(
        content=ft.Row(
            [ft.Icon(icon, size=20), ft.Text(label, size=14)],
            spacing=12,
        ),
        tooltip=label,
        style=_nav_style(False),
        on_click=on_click,
    )


class _Sidebar(ft.Container):
    """Navegación lateral: Inicio y herramientas agrupadas por categoría.

    Sustituye al NavigationRail, que no tiene scroll: con más herramientas las
    entradas dejarían de caber en la ventana. Botones normales, así que se
    recorre con el teclado como el resto de la app.
    """

    def __init__(self, tools, on_home, on_tool) -> None:
        self.home_button = _nav_button(
            ft.Icons.GRID_VIEW, "Inicio", lambda _e: on_home()
        )
        self.tool_buttons: list[ft.TextButton] = [
            _nav_button(tool.meta.icon, tool.meta.name, lambda _e, i=index: on_tool(i))
            for index, tool in enumerate(tools)
        ]
        controls: list[ft.Control] = [self.home_button]
        for category, items in _group_by_category(tools):
            controls.append(
                ft.Container(
                    ft.Text(
                        category,
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    padding=ft.padding.only(left=12, top=12, bottom=2),
                )
            )
            controls.extend(self.tool_buttons[i] for i, _tool in items)
        self.list = ft.ListView(controls, spacing=2, padding=8, expand=True)
        super().__init__(content=self.list, width=208)

    def select(self, index: int | None) -> None:
        """Marca Inicio (None) o la herramienta `index` como actual."""
        self.home_button.style = _nav_style(index is None)
        for i, button in enumerate(self.tool_buttons):
            button.style = _nav_style(i == index)


class _UpdateBanner(ft.Banner):
    """Aviso de nueva versión: colores del tema y siempre se puede cerrar."""

    def __init__(self, page) -> None:
        self._app_page = page
        self._url: str | None = None
        super().__init__(
            content=ft.Text(
                "Hay una nueva versión disponible. ¿Descargarla ahora?",
                color=ft.Colors.ON_SECONDARY_CONTAINER,
            ),
            leading=ft.Icon(
                ft.Icons.SYSTEM_UPDATE, color=ft.Colors.ON_SECONDARY_CONTAINER
            ),
            bgcolor=ft.Colors.SECONDARY_CONTAINER,
            actions=[
                ft.TextButton("Descargar", on_click=self._download),
                ft.TextButton("Ahora no", on_click=self._dismiss),
            ],
        )

    def show(self, url: str) -> None:
        self._url = url

    def _download(self, _e) -> None:
        if self._url:
            self._app_page.launch_url(self._url)
        self._dismiss(_e)

    def _dismiss(self, _e) -> None:
        self._app_page.close(self)


def _build_update_banner(page) -> _UpdateBanner:
    return _UpdateBanner(page)


def _start_update_check(
    on_found: Callable[[str], None], check: Callable[[], str | None]
) -> threading.Thread:
    """Busca una versión nueva en un hilo propio.

    No usa el pool de trabajos: con solo dos workers, una red lenta no debe
    retrasar la primera tarea del usuario. `check` nunca lanza (ver updater).
    """

    def target() -> None:
        url = check()
        if url:
            on_found(url)

    thread = threading.Thread(target=target, name="pdftool-update-check", daemon=True)
    thread.start()
    return thread


_MODE_NAMES = {"system": "Sistema", "light": "Claro", "dark": "Oscuro"}


def _theme_label(mode: str) -> str:
    return f"Tema: {_MODE_NAMES[mode]} · cambiar a {_MODE_NAMES[next_mode(mode)]}"


def _configure_window(page) -> None:
    page.window.width = 980
    page.window.height = 680
    # Barra lateral (208) + contenido: por debajo de esto los controles de los
    # paneles dejan de caber.
    page.window.min_width = 820
    page.window.min_height = 560


def _handle_shortcut(event, tool) -> bool:
    """⌘/Ctrl+O añade archivos y ⌘/Ctrl+Enter ejecuta en la herramienta abierta.

    Devuelve True si el evento era un atajo (aunque no hubiera nada que hacer).
    """
    if tool is None or not (event.ctrl or event.meta):
        return False
    if event.key.upper() == "O":
        tool.shortcut_open()
        return True
    if event.key == "Enter":
        tool.shortcut_run()
        return True
    return False


def _notify(page, message: str) -> None:
    page.open(ft.SnackBar(ft.Text(message)))


def build_app(page: ft.Page) -> None:
    registry.discover()
    tools = registry.get_tools()
    settings = load_settings()

    # Libera los workers compartidos cuando Flet cierra la sesión de escritorio
    # o desconecta la vista web. Las tareas en curso ya tienen además su propio
    # token de generación y dejan de notificar a la UI obsoleta.
    def shutdown_resources(_e=None) -> None:
        shutdown_job_executor()
        shutdown_thumbnail_executor()

    page.on_close = shutdown_resources
    page.on_disconnect = shutdown_resources

    page.title = f"pdf-tool · v{__version__}"
    page.theme = build_theme()
    page.theme_mode = resolve_mode(settings.theme_mode)
    _configure_window(page)

    ctx = ToolContext(page=page, run_job=run_job, settings=settings)
    content = ft.Container(expand=True, padding=24)

    current: list = [None]  # herramienta abierta (None = Inicio)

    def open_tool(index: int) -> None:
        content.content = tools[index].build_panel(ctx)
        current[0] = tools[index]
        sidebar.select(index)
        page.update()

    def open_home() -> None:
        content.content = _build_home(tools, open_tool)
        current[0] = None
        sidebar.select(None)
        page.update()

    page.on_keyboard_event = lambda e: _handle_shortcut(e, current[0])

    sidebar = _Sidebar(tools, on_home=open_home, on_tool=open_tool)

    def toggle_theme(_e) -> None:
        settings.theme_mode = next_mode(settings.theme_mode)
        save_settings(settings)
        page.theme_mode = resolve_mode(settings.theme_mode)
        refresh_theme_label()
        page.update()

    def refresh_theme_label() -> None:
        theme_item.text = _theme_label(settings.theme_mode)

    update_banner = _build_update_banner(page)

    log_picker = make_log_picker(
        on_saved=lambda path: _notify(page, f"Informe guardado en «{path.name}».")
    )
    page.overlay.append(log_picker)

    footer, theme_item = _build_footer(
        "Cambiar tema",
        toggle_theme,
        download_log_button(log_picker).on_click,
        lambda _e: page.launch_url(AUTHOR_SITE),
    )
    refresh_theme_label()

    page.add(
        ft.Column(
            [
                ft.Row([sidebar, ft.VerticalDivider(width=1), content], expand=True),
                ft.Divider(height=1),
                footer,
            ],
            expand=True,
        )
    )
    open_home()

    def _on_update(url: str) -> None:
        update_banner.show(url)
        page.open(update_banner)

    _start_update_check(
        _on_update, lambda: check_for_update(current=__version__, repo=GITHUB_REPO)
    )
