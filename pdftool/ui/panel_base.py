from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import flet as ft

from pdftool.core.jobs import JobHandle
from pdftool.core.plugin import PdfTool, ToolContext, ToolResult
from pdftool.ui.errors import humanize_error
from pdftool.ui.logs import download_log_button, make_log_picker
from pdftool.ui.output_dir import OutputDirField
from pdftool.ui.platform import open_file, open_folder

_WEB_MODE_MSG = "El modo navegador no da rutas locales; usa la app de escritorio."


class InvalidParams(Exception):
    """Params inválidos; el panel muestra str(exc) en el status.

    Si se indica `field`, el mensaje también se marca en ese campo.
    """

    def __init__(self, message: str, field: ft.TextField | None = None) -> None:
        super().__init__(message)
        self.field = field


_FORBIDDEN_NAME_CHARS = set('/\\:?|<>*"\x00')

# Nombres que Windows no permite como archivo, con o sin extensión.
_WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def parse_output_name(value: str | None) -> str | None:
    """Sanitiza el nombre de salida escrito por el usuario.

    None si quedó vacío (→ nombre default); sin extensión .pdf (se añade sola
    en la lógica). Lanza InvalidParams si trae separadores de ruta.
    """
    name = (value or "").strip()
    if name.lower().endswith(".pdf"):
        name = name[:-4].strip()
    if not name:
        return None
    if any(c in _FORBIDDEN_NAME_CHARS for c in name):
        raise InvalidParams(
            'Nombre de salida inválido: no puede contener / \\ : ? | < > * "'
        )
    if name.upper() in _WINDOWS_RESERVED_NAMES:
        raise InvalidParams(
            f"Nombre de salida inválido: {name!r} está reservado por Windows."
        )
    return name


_HELPER_OK_COLOR = ft.Colors.ON_SURFACE_VARIANT
# Token del tema (no un ámbar fijo): legible en claro y en oscuro.
_HELPER_WARN_COLOR = ft.Colors.TERTIARY

# Tipo de mensaje de estado → (icono, color del icono, color del texto).
# El color nunca va solo: el icono y el propio texto llevan el significado.
_STATUS_STYLES: dict[str, tuple[str | None, str | None, str | None]] = {
    "info": (None, None, None),
    "success": (ft.Icons.CHECK_CIRCLE, ft.Colors.PRIMARY, None),
    "partial": (ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.ERROR, None),
    "error": (ft.Icons.ERROR_OUTLINE, ft.Colors.ERROR, ft.Colors.ERROR),
}


class OutputNameField(ft.TextField):
    """Campo opcional para la base del archivo de salida.

    Muestra en vivo el nombre final que se usará. `resolve` devuelve la ruta
    que la herramienta escribiría para esa base, o None si aún no hay archivos;
    así la UI no reimplementa la regla de colisión, la consulta.
    """

    def __init__(self, resolve: Callable[[str | None], Path | None]) -> None:
        super().__init__(hint_text="Nombre de salida (opcional)", width=280, dense=True)
        self._resolve = resolve
        self.on_change = lambda _e: self.refresh(update=True)

    def refresh(self, update: bool = False) -> None:
        text, color = self._helper()
        self.helper_text = text
        self.helper_style = ft.TextStyle(size=11, color=color) if text else None
        if update and self.page:
            self.update()

    def _helper(self) -> tuple[str | None, str | None]:
        try:
            base = parse_output_name(self.value)
        except InvalidParams:
            return None, None
        if base is None:
            return None, None
        out = self._resolve(base)
        if out is None:
            return None, None
        if out.name == f"{base}.pdf":
            return f"Se guardará como «{out.name}»", _HELPER_OK_COLOR
        return f"Ya existe — se guardará como «{out.name}»", _HELPER_WARN_COLOR


class BaseToolPanel(PdfTool):
    # Rellenados por cada herramienta:
    run_label: str = "Aplicar"
    run_icon = ft.Icons.PLAY_ARROW
    pick_label: str = "Elegir PDF"
    pick_icon = ft.Icons.UPLOAD_FILE
    allowed_extensions: list[str] = ["pdf"]
    # Las listas de lotes necesitan ocupar el espacio disponible cuando hay
    # archivos. Los paneles de un solo archivo no: un cuerpo vacío solo aleja la
    # acción principal de los controles que la preparan.
    expand_body_when_ready = True

    # Controles que `build_panel` crea una vez por página (ver ese método).
    _root: ft.Column | None = None
    _out_dir: OutputDirField
    _ctx: ToolContext
    _page: Any  # ft.Page; los tests usan un sustituto mínimo
    progress: ft.ProgressBar
    status: ft.Text
    _status_icon: ft.Icon
    _status_row: ft.Row
    _counter: ft.Text
    _error_toggle: ft.TextButton
    _error_detail: ft.Text
    _log_btn: ft.Control
    _error_actions: ft.Row
    open_btn: ft.FilledButton
    open_file_btn: ft.FilledButton
    run_btn: ft.FilledButton
    cancel_btn: ft.OutlinedButton
    _result_actions: ft.Row
    _feedback: ft.Column
    _body: ft.Control
    _empty_hint: ft.Text

    def __init__(self) -> None:
        super().__init__()
        # Un único FilePicker reutilizado entre renders (evita fugas en overlay).
        self._picker = ft.FilePicker()
        # Ídem, para el informe de diagnóstico; confirma dónde quedó guardado.
        self._log_picker = make_log_picker(
            on_saved=lambda path: self._notify(f"Informe guardado en «{path.name}».")
        )
        self._invalid_field: ft.TextField | None = None
        self._job: JobHandle | None = None
        self._generation = 0

    def _invalidate_active_job(self, *, reset_ui: bool = True) -> None:
        """Invalida callbacks antiguos y solicita cancelar su trabajo."""
        self._generation += 1
        if self._job is not None:
            self._job.cancel()
            self._job = None
        if reset_ui and hasattr(self, "progress"):
            self.progress.visible = False
            self.progress.value = 0
            self.cancel_btn.visible = False
            self.run_btn.disabled = not self.can_run()

    # ---- hooks de la herramienta ----
    def extra_controls(self) -> list[ft.Control]:
        return []

    def on_inputs_changed(self) -> None:
        """Hook: la lista de archivos cambió. Los paneles con campos que
        dependen de las entradas lo sobrescriben."""

    def on_output_dir_changed(self) -> None:
        """Hook: cambió la carpeta de salida. Los paneles que predicen el
        nombre final lo sobrescriben."""

    def make_params(self):
        raise NotImplementedError

    def run_logic(self, inputs: list[Path], params, progress) -> ToolResult:
        raise NotImplementedError

    def on_result(self, result: ToolResult) -> None:
        """Hook opcional tras un run correcto (p. ej. anotar la lista de archivos)."""

    # ---- hooks de la subclase (1 archivo / N archivos) ----
    def build_input(self, page) -> ft.Control:
        """Barra de entrada de la zona superior (botones de elegir/limpiar)."""
        raise NotImplementedError

    def build_body(self) -> ft.Control:
        """Zona flexible del medio; el único control con expand=True."""
        raise NotImplementedError

    def collect_inputs(self) -> list[Path]:
        raise NotImplementedError

    def can_run(self) -> bool:
        raise NotImplementedError

    def _empty_action_hint(self) -> str:
        """Explica junto al botón qué falta para poder ejecutar."""
        required = getattr(self, "min_files", 1)
        selected = sum(path is not None for path in self.collect_inputs())
        remaining = max(required - selected, 0)
        if remaining == 0:
            return ""
        if required == 1:
            return "Añade un archivo para continuar."
        if selected == 0:
            return f"Añade al menos {required} archivos para continuar."
        suffix = "archivo" if remaining == 1 else "archivos"
        return f"Añade {remaining} {suffix} más para continuar."

    def _sync_ready_state(self) -> None:
        """Sincroniza acción, ayuda y densidad con las entradas actuales."""
        ready = self.can_run()
        self.run_btn.disabled = not ready
        self._empty_hint.value = "" if ready else self._empty_action_hint()
        self._empty_hint.visible = not ready
        self._body.expand = ready and self.expand_body_when_ready

    # ---- registro (log de diagnóstico; sin datos del usuario) ----
    def _logger(self) -> logging.Logger:
        return logging.getLogger(f"pdftool.{self.meta.id}")

    def _elapsed(self) -> float:
        started = getattr(self, "_run_started", None)
        return 0.0 if started is None else time.monotonic() - started

    def _notify(self, message: str, **snack) -> None:
        self._page.open(ft.SnackBar(ft.Text(message), **snack))

    def _mark_invalid(self, field: ft.TextField | None, message: str) -> None:
        self._clear_invalid()
        if field is not None:
            field.error_text = message
            self._invalid_field = field

    def _clear_invalid(self) -> None:
        if self._invalid_field is not None:
            self._invalid_field.error_text = None
            self._invalid_field = None

    # ---- estado (mensaje bajo la acción principal) ----
    def _set_status(self, text: str, kind: str = "info") -> None:
        icon, icon_color, text_color = _STATUS_STYLES[kind]
        self.status.value = text
        self.status.color = text_color
        self._status_icon.name = icon
        self._status_icon.color = icon_color
        self._status_icon.visible = bool(text) and icon is not None

    # ---- acciones post-run (footer) ----
    def _show_result_actions(self, result: ToolResult) -> None:
        self._hide_result_actions()
        if not result.outputs:
            return
        self._result_actions.visible = True
        # Tras completar, abrir el resultado prima sobre volver a procesarlo.
        self.run_btn.style = ft.ButtonStyle(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, color=ft.Colors.ON_SURFACE
        )
        self.open_btn.visible = True
        self.open_btn.style = (
            ft.ButtonStyle(
                bgcolor=ft.Colors.SECONDARY_CONTAINER,
                color=ft.Colors.ON_SECONDARY_CONTAINER,
            )
            if len(result.outputs) == 1
            else None
        )
        self.open_btn.data = result.outputs[0].parent
        self.open_file_btn.visible = len(result.outputs) == 1
        self.open_file_btn.data = result.outputs[0]

    def _hide_result_actions(self) -> None:
        self._result_actions.visible = False
        self.open_btn.visible = False
        self.open_file_btn.visible = False
        self.open_btn.data = None
        self.open_file_btn.data = None
        self.run_btn.style = None

    def _cancel_run(self, _e) -> None:
        """Detiene el trabajo en curso; lo ya publicado se queda en disco."""
        if self._job is None:
            return
        self._logger().info("cancelado · %.1fs", self._elapsed())
        self._invalidate_active_job()
        self._set_status("Cancelado. Los archivos ya terminados se conservan.", "info")
        self._page.update()

    # ---- errores (mensajes para el usuario) ----
    def _clear_error(self) -> None:
        self._error_toggle.visible = False
        self._error_toggle.text = "Ver detalle técnico"
        self._error_detail.visible = False
        self._error_detail.value = ""
        self._log_btn.visible = False
        self._error_actions.visible = False

    def _toggle_error_detail(self, _e) -> None:
        self._error_detail.visible = not self._error_detail.visible
        self._error_toggle.text = (
            "Ocultar detalle" if self._error_detail.visible else "Ver detalle técnico"
        )
        self._page.update()

    def _on_error(self, exc: Exception, generation: int | None = None) -> None:
        if generation is not None and generation != self._generation:
            return
        self._job = None
        self._hide_result_actions()
        self._logger().error("error · %.1fs", self._elapsed(), exc_info=exc)
        self.progress.visible = False
        self.cancel_btn.visible = False
        message, detail = humanize_error(exc)
        self._set_status(message, "error")
        if detail:
            self._error_detail.value = detail
            self._error_detail.visible = False  # arranca plegado
            self._error_toggle.visible = True
            self._log_btn.visible = True
            self._error_actions.visible = True
        else:
            self._clear_error()
        self.run_btn.disabled = not self.can_run()
        self._page.update()

    # ---- común ----
    def build_panel(self, ctx: ToolContext) -> ft.Control:
        # El panel se construye una vez por página y se reutiliza: navegar a
        # otra herramienta y volver conserva archivos, campos, resultado y el
        # trabajo en curso (sus callbacks siguen actualizando estos controles).
        root = self._root
        if root is not None and self._ctx.page is ctx.page:
            self._ctx = ctx
            # El destino es global (vive en Settings): otra herramienta pudo
            # cambiarlo mientras este panel estaba oculto.
            self._out_dir.sync()
            return root
        # Página nueva (otra sesión): nada del panel anterior debe notificar.
        self._invalidate_active_job()
        self._ctx = ctx
        page: Any = ctx.page
        self._page = page

        self.progress = ft.ProgressBar(value=0, visible=False)
        self.status = ft.Text("", weight=ft.FontWeight.W_500, expand=True)
        self._status_icon = ft.Icon(visible=False, size=20)
        self._status_row = ft.Row(
            [self._status_icon, self.status],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
        self._counter = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._error_toggle = ft.TextButton(
            "Ver detalle técnico", visible=False, on_click=self._toggle_error_detail
        )
        self._error_detail = ft.Text(
            "",
            visible=False,
            selectable=True,
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._log_btn = download_log_button(self._log_picker)
        self._log_btn.visible = False
        self._error_actions = ft.Row(
            [self._error_toggle, self._log_btn], visible=False, wrap=True
        )
        self.open_btn = ft.FilledButton(
            "Abrir carpeta", icon=ft.Icons.FOLDER_OPEN, visible=False
        )
        self.open_file_btn = ft.FilledButton(
            "Abrir archivo", icon=ft.Icons.OPEN_IN_NEW, visible=False
        )
        self.run_btn = ft.FilledButton(
            self.run_label, icon=self.run_icon, disabled=True
        )
        self.cancel_btn = ft.OutlinedButton(
            "Cancelar", icon=ft.Icons.STOP, visible=False, on_click=self._cancel_run
        )
        self._result_actions = ft.Row(
            [self.open_file_btn, self.open_btn], visible=False, wrap=True, spacing=8
        )
        self._feedback = ft.Column(
            [
                self.progress,
                self._status_row,
                self._result_actions,
                self._error_actions,
                self._error_detail,
            ],
            spacing=8,
            tight=True,
        )

        # Una única instancia por panel: cada OutputDirField trae su propio
        # FilePicker, que se quedaría en page.overlay. Mismo motivo que
        # self._picker.
        if not hasattr(self, "_out_dir"):
            self._out_dir = OutputDirField(
                ctx.settings, on_change=self.on_output_dir_changed
            )
        self._out_dir.attach(page)
        self._out_dir.sync()

        input_bar = self.build_input(page)  # subclase; fija self._picker.on_result
        body = self.build_body()
        self._body = body
        self._empty_hint = ft.Text(
            "",
            size=14,
            color=ft.Colors.ON_SURFACE_VARIANT,
            visible=False,
        )
        self._sync_ready_state()

        if self._picker not in page.overlay:
            page.overlay.append(self._picker)

        if self._log_picker not in page.overlay:
            page.overlay.append(self._log_picker)

        def do_run(_e) -> None:
            if not self.can_run():
                return
            self._clear_error()
            self._clear_invalid()
            self._hide_result_actions()
            if self._out_dir.destination_missing():
                self._set_status(
                    "La carpeta de destino ya no está disponible. Elige otra "
                    "o vuelve a «junto al original».",
                    "error",
                )
                page.update()
                return
            try:
                params = self.make_params().model_copy(
                    update={"output_dir": self._out_dir.value}
                )
            except InvalidParams as exc:
                self._set_status(str(exc), "error")
                self._mark_invalid(exc.field, str(exc))
                page.update()
                return
            self.run_btn.disabled = True
            self.cancel_btn.visible = True
            self.progress.visible = True
            self.progress.value = 0
            self._set_status("Procesando…")
            page.update()
            inputs = self.collect_inputs()
            self._invalidate_active_job(reset_ui=False)
            run_generation = self._generation
            self._run_started = time.monotonic()
            self._logger().info("inicio · %d archivo(s)", len(inputs))

            def is_current() -> bool:
                return self._generation == run_generation

            def set_progress(pct: float, msg: str) -> None:
                if not is_current():
                    return
                self.progress.value = pct
                self._set_status(msg)
                page.update()

            def on_done(result: ToolResult) -> None:
                if not is_current():
                    return
                self._job = None
                self._logger().info("ok · %.1fs", self._elapsed())
                self._clear_error()
                self.progress.visible = False
                self.cancel_btn.visible = False
                failed = any(not item.ok for item in result.items or [])
                self._set_status(result.summary, "partial" if failed else "success")
                self._show_result_actions(result)
                self.run_btn.disabled = not self.can_run()
                self.on_result(result)
                page.update()

            self._job = ctx.run_job(
                work=lambda prog: self.run_logic(inputs, params, prog),
                on_progress=set_progress,
                on_done=on_done,
                on_error=lambda exc: self._on_error(exc, run_generation),
                is_current=is_current,
            )

        self.run_btn.on_click = do_run
        self.open_btn.on_click = lambda _e: open_folder(Path(self.open_btn.data))
        self.open_file_btn.on_click = lambda _e: open_file(self.open_file_btn.data)

        # Tres zonas: superior fija · cuerpo flexible · footer anclado.
        # `body` es el único hijo con expand=True: todo lo posterior queda
        # pegado al fondo sin importar cuántos archivos haya en la lista.
        self._root = ft.Column(
            [
                ft.Text(self.meta.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(self.meta.description),
                ft.Divider(),
                input_bar,
                *self.extra_controls(),
                body,
                ft.Divider(),
                self._out_dir,
                self._empty_hint,
                ft.Row(
                    [
                        self.run_btn,
                        self.cancel_btn,
                        ft.Container(expand=True),
                        self._counter,
                    ]
                ),
                self._feedback,
            ],
            spacing=16,
            expand=True,
        )
        return self._root


class SingleFileToolPanel(BaseToolPanel):
    expand_body_when_ready = False

    def build_input(self, page) -> ft.Control:
        self._file: Path | None = None
        self._file_label = ft.Text("Ningún archivo seleccionado", italic=True)
        self._picker.on_result = self._on_pick
        return ft.Row(
            [
                ft.FilledTonalButton(
                    self.pick_label,
                    icon=self.pick_icon,
                    on_click=lambda _e: self._picker.pick_files(
                        allow_multiple=False, allowed_extensions=self.allowed_extensions
                    ),
                ),
                self._file_label,
            ]
        )

    def build_body(self) -> ft.Control:
        return ft.Container(expand=True)  # empuja el footer al fondo

    def _on_pick(self, e) -> None:
        if e.files and e.files[0].path:
            self._invalidate_active_job()
            self._file = Path(e.files[0].path)
            self._file_label.value = self._file.name
            self._file_label.italic = False
            self._hide_result_actions()
            self._set_status("")
            self._clear_error()
            self._sync_ready_state()
            try:
                self.after_pick(self._file)
            except Exception as exc:  # p. ej. un PDF dañado al leer sus páginas
                self._reject_pick(exc)
        elif e.files:
            self._set_status(_WEB_MODE_MSG)
            self._clear_error()
        self._page.update()

    def after_pick(self, path: Path) -> None:
        """Hook opcional tras elegir un archivo válido (p.ej. leer nº de páginas).

        Si lanza, la selección se descarta y el error se muestra al usuario.
        """

    def _reject_pick(self, exc: Exception) -> None:
        self._logger().warning("no se pudo leer la entrada", exc_info=exc)
        self._file = None
        self._file_label.value = "Ningún archivo seleccionado"
        self._file_label.italic = True
        self._sync_ready_state()
        self._set_status(humanize_error(exc)[0], "error")

    def collect_inputs(self) -> list[Path]:
        return [] if self._file is None else [self._file]

    def can_run(self) -> bool:
        return self._file is not None
