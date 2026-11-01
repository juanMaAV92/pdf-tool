from __future__ import annotations

import threading
from collections.abc import Callable

import flet as ft

from pdftool import __version__
from pdftool.core.config import load_settings, save_settings
from pdftool.core.jobs import run_job, shutdown_job_executor
from pdftool.core.plugin import ToolContext
from pdftool.core.updater import GITHUB_REPO, check_for_update
from pdftool.i18n import (
    available_languages,
    current_language,
    resolve_language,
    set_language,
    t,
)
from pdftool.ui import registry
from pdftool.ui.accessibility import icon_content
from pdftool.ui.logs import download_log_button, log_label, make_log_picker
from pdftool.ui.theme import build_theme, next_mode, resolve_mode
from pdftool.ui.thumbnails import shutdown_thumbnail_executor

AUTHOR_HANDLE = "@juanmaav92"
# El pie lleva a la página del producto (ayuda, instalación, novedades).
PRODUCT_SITE = "https://juanmaav92.github.io/pdf-tool"


def _build_footer(
    theme_label, on_theme, on_log, on_site, language_item=None, on_menu_open=None
):
    """Pie: firma del autor a la izquierda; versión y utilidades a la derecha.

    Devuelve (pie, ítem del tema): el ítem se reetiqueta al cambiar el tema.
    """
    theme_item = ft.PopupMenuItem(
        text=theme_label, icon=ft.Icons.BRIGHTNESS_6, on_click=on_theme
    )
    items = [theme_item]
    if language_item is not None:
        items.append(language_item)
    items.append(
        ft.PopupMenuItem(text=log_label(), icon=ft.Icons.DOWNLOAD, on_click=on_log)
    )
    # Visible en todas las pantallas pero discreta: mismo tono apagado y
    # tamaño que la versión, sin competir con el resultado del panel.
    credit = ft.TextButton(
        t("ui.footer.credit", handle=AUTHOR_HANDLE),
        icon=ft.Icons.OPEN_IN_NEW,
        tooltip=t("ui.footer.credit_tooltip"),
        on_click=on_site,
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
                tooltip=t("ui.footer.version", version=__version__),
            ),
            ft.PopupMenuButton(
                content=icon_content(ft.Icons.MORE_HORIZ, t("ui.footer.options")),
                tooltip=t("ui.footer.options"),
                items=items,
                on_open=on_menu_open,
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
                        ft.Icon(tool.icon, size=30),
                        ft.Text(
                            tool.meta.category_label,
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
    """[(id de categoría, [(índice, herramienta), …]), …] respetando el orden de
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
            ft.Text(t("ui.home.title"), size=28, weight=ft.FontWeight.BOLD),
            ft.Text(t("ui.home.subtitle")),
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
            ft.Icons.GRID_VIEW, t("ui.nav.home"), lambda _e: on_home()
        )
        self.tool_buttons: list[ft.TextButton] = [
            _nav_button(tool.icon, tool.meta.name, lambda _e, i=index: on_tool(i))
            for index, tool in enumerate(tools)
        ]
        controls: list[ft.Control] = [self.home_button]
        for _category, items in _group_by_category(tools):
            controls.append(
                ft.Container(
                    ft.Text(
                        items[0][1].meta.category_label,
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


class _UpdateBanner(ft.Container):
    """Aviso de nueva versión como barra dentro de la ventana, encima del contenido.

    No es un `ft.Banner`: abierto con `page.open` se dibujaba como capa encima,
    oscurecido y tapando el título. Aquí empuja el contenido hacia abajo, y los
    pares PRIMARY_CONTAINER / ON_PRIMARY_CONTAINER dan buen contraste en tema claro
    y oscuro. Siempre se puede cerrar.
    """

    def __init__(self, page) -> None:
        self._app_page = page
        self._url: str | None = None
        self.text = ft.Text(
            t("ui.update.text"),
            color=ft.Colors.ON_PRIMARY_CONTAINER,
            weight=ft.FontWeight.W_500,
            expand=True,
        )
        self.download_button = ft.FilledButton(
            t("ui.update.download"), on_click=self._download
        )
        self.dismiss_button = ft.TextButton(
            t("ui.update.dismiss"),
            on_click=self._dismiss,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY_CONTAINER),
        )
        super().__init__(
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.SYSTEM_UPDATE, color=ft.Colors.ON_PRIMARY_CONTAINER
                    ),
                    self.text,
                    self.dismiss_button,
                    self.download_button,
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            visible=False,
        )

    def show(self, url: str) -> None:
        self._url = url
        self.visible = True
        self._app_page.update()

    def _download(self, _e) -> None:
        if self._url:
            self._app_page.launch_url(self._url)
        self._dismiss(_e)

    def _dismiss(self, _e) -> None:
        self.visible = False
        self._app_page.update()


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


def _theme_label(mode: str) -> str:
    return t(
        "ui.theme.label",
        current=t(f"ui.theme.{mode}"),
        next=t(f"ui.theme.{next_mode(mode)}"),
    )


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


def _install_shutdown_hooks(page, shutdown: Callable[[], None]) -> None:
    """Engancha `shutdown` al cierre y a la desconexión de la página.

    Como corrutinas: Flet ejecuta los manejadores síncronos en su pool de
    hilos, que al cerrar la ventana ya está apagado, y el cierre acababa con
    «cannot schedule new futures after shutdown». `shutdown` no bloquea.
    """

    async def on_shutdown(_e) -> None:
        shutdown()

    page.on_close = on_shutdown
    page.on_disconnect = on_shutdown


def _notify(page, message: str) -> None:
    page.open(ft.SnackBar(ft.Text(message)))


def any_task_running(tools) -> bool:
    """Alguna herramienta tiene una tarea en curso (bloquea cambiar el idioma)."""
    return any(getattr(tool, "_running", False) for tool in tools)


def _language_label() -> str:
    names = dict(available_languages())
    return t("ui.language.menu", name=names.get(current_language(), current_language()))


def _language_dialog(page, settings, on_choose) -> ft.AlertDialog:
    """Diálogo con «Idioma del sistema» y cada idioma por su nombre propio."""
    options = [("system", t("ui.language.system")), *available_languages()]
    group = ft.RadioGroup(
        value=settings.language,
        content=ft.Column([ft.Radio(value=code, label=name) for code, name in options]),
    )
    dialog = ft.AlertDialog(title=ft.Text(t("ui.language.title")), content=group)

    def chosen(_e) -> None:
        page.close(dialog)
        if group.value and group.value != settings.language:
            on_choose(group.value)

    group.on_change = chosen
    dialog.actions = [
        ft.TextButton(t("ui.language.cancel"), on_click=lambda _e: page.close(dialog))
    ]
    return dialog


# Estado de la app montada por página: herramientas e ítem de idioma.
_STATE: dict[int, dict] = {}


def current_tools(page) -> list:
    return _STATE[id(page)]["tools"]


def refresh_language_item(page) -> None:
    """Desactiva el ítem de idioma mientras haya una tarea en curso."""
    state = _STATE[id(page)]
    item = state["language_item"]
    busy = any_task_running(state["tools"])
    item.disabled = busy
    item.text = _language_label()
    item.tooltip = t("ui.language.busy") if busy else None


def choose_language(page, settings, code: str) -> None:
    """Guarda el idioma y reconstruye la interfaz en él, al momento."""
    if any_task_running(current_tools(page)):
        return
    settings.language = code
    save_settings(settings)
    set_language(resolve_language(code))
    _mount(page, settings)
    page.update()


def build_app(page: ft.Page) -> None:
    settings = load_settings()
    set_language(resolve_language(settings.language))

    # Libera los workers compartidos cuando Flet cierra la sesión de escritorio
    # o desconecta la vista web. Las tareas en curso ya tienen además su propio
    # token de generación y dejan de notificar a la UI obsoleta.
    def shutdown_resources() -> None:
        shutdown_job_executor()
        shutdown_thumbnail_executor()

    _install_shutdown_hooks(page, shutdown_resources)

    page.title = f"pdf-tool · v{__version__}"
    page.theme = build_theme()
    page.theme_mode = resolve_mode(settings.theme_mode)
    _configure_window(page)
    _mount(page, settings)

    def _on_update(url: str) -> None:
        _STATE[id(page)]["update_url"] = url
        _STATE[id(page)]["banner"].show(url)

    _start_update_check(
        _on_update, lambda: check_for_update(current=__version__, repo=GITHUB_REPO)
    )


def _mount(page, settings) -> None:
    """Monta (o vuelve a montar, al cambiar de idioma) toda la interfaz.

    Herramientas nuevas: sus textos se crean en el idioma activo. Se retiran
    los controles y los `FilePicker` del montaje anterior.
    """
    previous = _STATE.get(id(page), {})
    page.controls.clear()
    page.overlay.clear()
    registry.discover()
    tools = registry.get_tools()

    def busy_changed() -> None:
        refresh_language_item(page)
        page.update()

    ctx = ToolContext(
        page=page, run_job=run_job, settings=settings, on_busy_changed=busy_changed
    )
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
        on_saved=lambda path: _notify(page, t("ui.log.saved", name=path.name))
    )
    page.overlay.append(log_picker)

    language_item = ft.PopupMenuItem(
        text=_language_label(), icon=ft.Icons.TRANSLATE, data="language"
    )

    def open_language(_e) -> None:
        if any_task_running(tools):
            return
        page.open(
            _language_dialog(
                page, settings, lambda code: choose_language(page, settings, code)
            )
        )

    language_item.on_click = open_language

    footer, theme_item = _build_footer(
        _theme_label(settings.theme_mode),
        toggle_theme,
        download_log_button(log_picker).on_click,
        lambda _e: page.launch_url(PRODUCT_SITE),
        language_item,
        # Al abrir el menú: el ítem de idioma refleja si hay una tarea en curso.
        lambda _e: refresh_language_item(page),
    )

    _STATE[id(page)] = {
        "tools": tools,
        "language_item": language_item,
        "banner": update_banner,
        "update_url": previous.get("update_url"),
    }

    page.add(
        ft.Column(
            [
                update_banner,
                ft.Row([sidebar, ft.VerticalDivider(width=1), content], expand=True),
                ft.Divider(height=1),
                footer,
            ],
            expand=True,
        )
    )
    open_home()
    if previous.get("update_url"):
        update_banner.show(previous["update_url"])
