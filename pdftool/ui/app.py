from __future__ import annotations

import flet as ft

from pdftool import __version__
from pdftool.core import registry
from pdftool.core.config import load_settings, save_settings
from pdftool.core.jobs import run_job
from pdftool.core.plugin import ToolContext
from pdftool.core.updater import check_for_update
from pdftool.ui.theme import build_theme, next_mode, resolve_mode

GITHUB_REPO = "juanMaAV92/pdf-tool"
GITHUB_PROFILE = "https://github.com/juanMaAV92"


def build_app(page: ft.Page) -> None:
    registry.discover()
    tools = registry.get_tools()
    settings = load_settings()

    page.title = "pdf-tool"
    page.theme = build_theme()
    page.theme_mode = resolve_mode(settings.theme_mode)
    page.window.width = 980
    page.window.height = 680

    ctx = ToolContext(page=page, run_job=run_job)
    content = ft.Container(expand=True, padding=24)

    def show_tool(index: int) -> None:
        content.content = tools[index].build_panel(ctx)
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        destinations=[
            ft.NavigationRailDestination(icon=t.meta.icon, label=t.meta.name)
            for t in tools
        ],
        on_change=lambda e: show_tool(e.control.selected_index),
    )

    def toggle_theme(_e) -> None:
        settings.theme_mode = next_mode(settings.theme_mode)
        save_settings(settings)
        page.theme_mode = resolve_mode(settings.theme_mode)
        page.update()

    update_banner = ft.Banner(
        content=ft.Text("Hay una nueva versión disponible."),
        actions=[ft.TextButton("Descargar", on_click=lambda e: page.launch_url(e.control.data))],
        bgcolor=ft.Colors.AMBER_100,
        leading=ft.Icon(ft.Icons.SYSTEM_UPDATE),
    )

    top_bar = ft.Row(
        [
            ft.Text(f"pdf-tool v{__version__}", weight=ft.FontWeight.BOLD),
            ft.IconButton(ft.Icons.BRIGHTNESS_6, tooltip="Cambiar tema",
                          on_click=toggle_theme),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    footer = ft.Row(
        [
            ft.TextButton(
                "powered by juanMaAV92",
                icon=ft.Icons.OPEN_IN_NEW,
                tooltip="Abrir el perfil de GitHub del autor",
                on_click=lambda _e: page.launch_url(GITHUB_PROFILE),
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    page.add(
        ft.Column([
            top_bar,
            ft.Row([rail, ft.VerticalDivider(width=1), content], expand=True),
            ft.Divider(height=1),
            footer,
        ], expand=True)
    )
    if tools:
        show_tool(0)

    # Chequeo de actualización (no bloquea: corre en hilo).
    def _check(_progress=None):
        return check_for_update(current=__version__, repo=GITHUB_REPO)

    def _on_update(url):
        if url:
            update_banner.actions[0].data = url
            page.open(update_banner)

    run_job(_check, on_progress=lambda *_: None, on_done=_on_update,
            on_error=lambda *_: None)
