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


def _tool_card(index, tool, on_open):
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(tool.meta.icon, size=30),
                ft.Text(tool.meta.name, weight=ft.FontWeight.BOLD, size=15),
                ft.Text(tool.meta.description, size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            spacing=6,
        ),
        width=240,
        height=140,
        padding=16,
        border_radius=14,
        border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
        ink=True,
        on_click=lambda _e: on_open(index),
    )


def _build_home(tools, on_open):
    groups: dict[str, list] = {}
    for i, tool in enumerate(tools):
        groups.setdefault(tool.meta.category, []).append((i, tool))

    sections = [
        ft.Text("Herramientas PDF", size=28, weight=ft.FontWeight.BOLD),
        ft.Text("Elige una herramienta para empezar."),
        ft.Container(height=8),
    ]
    for category, items in groups.items():
        sections.append(ft.Text(category, size=18, weight=ft.FontWeight.BOLD))
        sections.append(
            ft.Row([_tool_card(i, t, on_open) for i, t in items],
                   wrap=True, spacing=12, run_spacing=12)
        )
    return ft.Column(sections, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)


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
        page.update()

    update_banner = ft.Banner(
        content=ft.Text("Hay una nueva versión disponible."),
        actions=[ft.TextButton("Descargar", on_click=lambda e: page.launch_url(e.control.data))],
        bgcolor=ft.Colors.AMBER_100,
        leading=ft.Icon(ft.Icons.SYSTEM_UPDATE),
    )

    top_bar = ft.Row(
        [
            ft.IconButton(ft.Icons.BRIGHTNESS_6, tooltip="Cambiar tema",
                          on_click=toggle_theme),
        ],
        alignment=ft.MainAxisAlignment.END,
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
    open_home()

    # Chequeo de actualización (no bloquea: corre en hilo).
    def _check(_progress=None):
        return check_for_update(current=__version__, repo=GITHUB_REPO)

    def _on_update(url):
        if url:
            update_banner.actions[0].data = url
            page.open(update_banner)

    run_job(_check, on_progress=lambda *_: None, on_done=_on_update,
            on_error=lambda *_: None)
