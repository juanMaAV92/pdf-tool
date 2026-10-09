from __future__ import annotations

import flet as ft

from pdftool import __version__
from pdftool.core import registry
from pdftool.core.config import load_settings, save_settings
from pdftool.core.jobs import run_job, shutdown_job_executor
from pdftool.core.plugin import ToolContext
from pdftool.core.updater import check_for_update
from pdftool.ui.accessibility import icon_content
from pdftool.ui.logs import download_log_button, make_log_picker
from pdftool.ui.theme import build_theme, next_mode, resolve_mode
from pdftool.ui.thumbnails import shutdown_thumbnail_executor

GITHUB_REPO = "juanMaAV92/pdf-tool"
GITHUB_PROFILE = "https://github.com/juanMaAV92"
AUTHOR_SITE = "https://juanMaAV92.github.io"


def _build_footer(theme_label, on_theme, on_log, on_author):
    """Utilidades globales secundarias; el resultado pertenece al panel."""
    return ft.Row(
        [
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
                    ft.PopupMenuItem(
                        text=theme_label, icon=ft.Icons.BRIGHTNESS_6, on_click=on_theme
                    ),
                    ft.PopupMenuItem(
                        text="Descargar log", icon=ft.Icons.DOWNLOAD, on_click=on_log
                    ),
                    ft.PopupMenuItem(
                        text="Acerca del autor",
                        icon=ft.Icons.OPEN_IN_NEW,
                        on_click=on_author,
                    ),
                ],
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )


def _tool_card(index, tool, on_open):
    return ft.OutlinedButton(
        content=ft.Column(
            [
                ft.Icon(tool.meta.icon, size=30),
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


def _build_home(tools, on_open):
    # Cuadrícula única que envuelve varias tarjetas por fila (compacta, sin scroll
    # con pocas herramientas). Cuando haya muchas por categoría, se puede agrupar.
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
    page.window.width = 980
    page.window.height = 680

    ctx = ToolContext(page=page, run_job=run_job, settings=settings)
    content = ft.Container(expand=True, padding=24)

    def open_tool(index: int) -> None:
        content.content = tools[index].build_panel(ctx)
        rail.selected_index = index + 1
        page.update()

    def open_home() -> None:
        content.content = _build_home(tools, open_tool)
        rail.selected_index = 0
        page.update()

    def on_rail_change(e) -> None:
        idx = e.control.selected_index
        if idx == 0:
            open_home()
        else:
            open_tool(idx - 1)

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.GRID_VIEW, label="Inicio"),
            *[
                ft.NavigationRailDestination(icon=t.meta.icon, label=t.meta.name)
                for t in tools
            ],
        ],
        on_change=on_rail_change,
    )

    def toggle_theme(_e) -> None:
        settings.theme_mode = next_mode(settings.theme_mode)
        save_settings(settings)
        page.theme_mode = resolve_mode(settings.theme_mode)
        refresh_theme_label()
        page.update()

    def refresh_theme_label() -> None:
        names = {"system": "sistema", "light": "claro", "dark": "oscuro"}
        label = (
            f"Tema: {names[settings.theme_mode]} → "
            f"{names[next_mode(settings.theme_mode)]}"
        )
        footer.controls[1].items[0].text = label

    update_banner = ft.Banner(
        content=ft.Text("Hay una nueva versión disponible."),
        actions=[
            ft.TextButton(
                "Descargar", on_click=lambda e: page.launch_url(e.control.data)
            )
        ],
        bgcolor=ft.Colors.AMBER_100,
        leading=ft.Icon(ft.Icons.SYSTEM_UPDATE),
    )

    log_picker = make_log_picker()
    page.overlay.append(log_picker)

    footer = _build_footer(
        "Cambiar tema",
        toggle_theme,
        download_log_button(log_picker).on_click,
        lambda _e: page.launch_url(AUTHOR_SITE),
    )
    refresh_theme_label()

    page.add(
        ft.Column(
            [
                ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True),
                ft.Divider(height=1),
                footer,
            ],
            expand=True,
        )
    )
    open_home()

    # Chequeo de actualización (no bloquea: corre en hilo).
    def _check(_progress=None):
        return check_for_update(current=__version__, repo=GITHUB_REPO)

    def _on_update(url):
        if url:
            update_banner.actions[0].data = url
            page.open(update_banner)

    run_job(
        _check,
        on_progress=lambda *_: None,
        on_done=_on_update,
        on_error=lambda *_: None,
    )
