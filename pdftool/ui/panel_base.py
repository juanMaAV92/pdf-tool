from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import flet as ft

from pdftool.core.errors import UserError
from pdftool.core.jobs import JobHandle
from pdftool.core.naming import parse_output_name
from pdftool.core.plugin import BaseParams, PdfTool, ToolContext, ToolResult, ToolSpec
from pdftool.i18n import t
from pdftool.ui.errors import humanize_error
from pdftool.ui.logs import download_log_button, make_log_picker
from pdftool.ui.output_dir import OutputDirField
from pdftool.ui.platform import open_file, open_folder, shortcut_label


class InvalidParams(UserError):
    """Params inválidos; el panel muestra str(exc) en el status.

    Si se indica `field`, el mensaje también se marca en ese campo. Cualquier
    `UserError` lanzado por `make_params` se trata igual, sin campo.
    """

    def __init__(self, message: str, field: ft.TextField | None = None) -> None:
        super().__init__(message)
        self.field = field


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
        super().__init__(hint_text=t("ui.output_name.hint"), width=280, dense=True)
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
        except UserError:
            return None, None
        if base is None:
            return None, None
        out = self._resolve(base)
        if out is None:
            return None, None
        if out.name == f"{base}.pdf":
            return t("ui.output_name.will_save", name=out.name), _HELPER_OK_COLOR
        return t("ui.output_name.exists", name=out.name), _HELPER_WARN_COLOR


class BaseToolPanel(PdfTool):
    # Rellenados por cada herramienta:
    icon: str = ""
    # Claves del diccionario (se traducen al construir el panel).
    run_label_key: str = "ui.panel.run"
    run_icon = ft.Icons.PLAY_ARROW
    pick_label_key: str = "ui.panel.pick_pdf"
    pick_icon = ft.Icons.UPLOAD_FILE
    allowed_extensions: tuple[str, ...] = ("pdf",)
    min_files: int = 1
    # Las listas de lotes necesitan ocupar el espacio disponible cuando hay
    # archivos. Los paneles de un solo archivo no: un cuerpo vacío solo aleja la
    # acción principal de los controles que la preparan.
    expand_body_when_ready = True
    # Función pura de la herramienta: run(inputs, params, progress) -> ToolResult.
    logic: Callable[..., ToolResult] | None = None
    # Definición sin Flet de la herramienta (`tools/<id>/spec.py`). Al
    # declararla, `meta` y `logic` salen de ella; un panel sin spec (p. ej. un
    # stub de test) los declara a mano.
    spec: ClassVar[ToolSpec | None] = None

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        spec = cls.__dict__.get("spec")
        if spec is not None:
            cls.meta = spec.meta
            cls.logic = staticmethod(spec.run)
            cls.min_files = spec.min_inputs
            cls.allowed_extensions = spec.extensions

    # Controles que `build_panel` crea una vez por página (ver ese método).
    _root: ft.Column | None = None
    # True mientras corre un trabajo: las entradas quedan bloqueadas (cambiar
    # archivos a mitad cancelaría el trabajo sin aviso; primero se cancela).
    _running = False
    _out_dir: OutputDirField
    _ctx: ToolContext
    _page: Any  # ft.Page; los tests usan un sustituto mínimo
    progress: ft.ProgressBar
    status: ft.Text
    _status_icon: ft.Icon
    _status_row: ft.Row
    _warnings: ft.Text
    _counter: ft.Text
    _error_toggle: ft.TextButton
    _error_detail: ft.Text
    _log_btn: ft.Control
    _error_actions: ft.Row
    open_btn: ft.FilledButton
    open_file_btn: ft.FilledButton
    run_btn: ft.FilledButton
    _pick_btn: ft.FilledTonalButton  # lo crea `build_input` de la subclase
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
            on_saved=lambda path: self._notify(t("ui.log.saved", name=path.name))
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
            self._set_running(False)
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
        """Ejecuta la lógica pura declarada en `logic` (en segundo plano)."""
        if self.logic is None:
            raise NotImplementedError("Declara `logic = staticmethod(<función>)`")
        return self.logic(inputs, params, progress=progress)

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
        required = self.min_files
        selected = sum(path is not None for path in self.collect_inputs())
        remaining = max(required - selected, 0)
        if remaining == 0:
            return ""
        if required == 1:
            return t("ui.panel.need_one")
        if selected == 0:
            return t("ui.panel.need_at_least", count=required)
        return t("ui.panel.need_more", count=remaining)

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.cancel_btn.visible = running
        self._lock_inputs(running)

    def _lock_inputs(self, locked: bool) -> None:
        """Hook: (des)habilita los controles que cambian las entradas."""

    def _sync_ready_state(self) -> None:
        """Sincroniza acción, ayuda y densidad con las entradas actuales."""
        ready = self.can_run()
        self.run_btn.disabled = not ready or self._running
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
        self._warnings.visible = False
        self._warnings.value = ""
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
        self._set_status(t("ui.panel.cancelled"), "info")
        self._page.update()

    # ---- errores (mensajes para el usuario) ----
    def _clear_error(self) -> None:
        self._error_toggle.visible = False
        self._error_toggle.text = t("ui.panel.show_detail")
        self._error_detail.visible = False
        self._error_detail.value = ""
        self._log_btn.visible = False
        self._error_actions.visible = False

    def _toggle_error_detail(self, _e) -> None:
        self._error_detail.visible = not self._error_detail.visible
        self._error_toggle.text = (
            t("ui.panel.hide_detail")
            if self._error_detail.visible
            else t("ui.panel.show_detail")
        )
        self._page.update()

    def _on_error(self, exc: Exception, generation: int | None = None) -> None:
        if generation is not None and generation != self._generation:
            return
        self._job = None
        self._hide_result_actions()
        self._logger().error("error · %.1fs", self._elapsed(), exc_info=exc)
        self.progress.visible = False
        self._set_running(False)
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

    # ---- atajos de teclado (los enruta el host) ----
    def shortcut_open(self) -> None:
        """⌘/Ctrl+O: el mismo efecto que pulsar el botón de añadir/elegir."""
        if not self._running and self._pick_btn.on_click is not None:
            self._pick_btn.on_click(None)

    def shortcut_run(self) -> None:
        """⌘/Ctrl+Enter: ejecuta solo si el botón está disponible."""
        if not self.run_btn.disabled:
            self._on_run_click(None)

    # ---- ejecución ----
    def _on_run_click(self, _e) -> None:
        params = self._prepare_run()
        if params is not None:
            self._start_job(params)

    def _prepare_run(self) -> BaseParams | None:
        """Valida destino y parámetros; None (con el error a la vista) si no."""
        if not self.can_run():
            return None
        self._clear_error()
        self._clear_invalid()
        self._hide_result_actions()
        if self._out_dir.destination_missing():
            self._set_status(
                t("ui.panel.destination_missing"),
                "error",
            )
            self._page.update()
            return None
        try:
            params: BaseParams = self.make_params()
        except UserError as exc:
            self._set_status(str(exc), "error")
            self._mark_invalid(getattr(exc, "field", None), str(exc))
            self._page.update()
            return None
        return params.model_copy(update={"output_dir": self._out_dir.value})

    def _start_job(self, params: BaseParams) -> None:
        self.run_btn.disabled = True
        self._set_running(True)
        self.progress.visible = True
        self.progress.value = 0
        self._set_status(t("ui.panel.processing"))
        self._page.update()
        inputs = self.collect_inputs()
        self._invalidate_active_job(reset_ui=False)
        generation = self._generation
        self._run_started = time.monotonic()
        self._logger().info("inicio · %d archivo(s)", len(inputs))
        self._job = self._ctx.run_job(
            work=lambda progress: self.run_logic(inputs, params, progress),
            on_progress=lambda pct, msg: self._on_run_progress(generation, pct, msg),
            on_done=lambda result: self._on_run_done(generation, result),
            on_error=lambda exc: self._on_error(exc, generation),
            is_current=lambda: self._generation == generation,
        )

    def _on_run_progress(self, generation: int, pct: float, msg: str) -> None:
        if generation != self._generation:
            return
        self.progress.value = pct
        self._set_status(msg)
        self._page.update()

    def _on_run_done(self, generation: int, result: ToolResult) -> None:
        if generation != self._generation:
            return
        self._job = None
        self._logger().info("ok · %.1fs", self._elapsed())
        self._clear_error()
        self.progress.visible = False
        self._set_running(False)
        failed = any(not item.ok for item in result.items or [])
        self._set_status(result.summary, "partial" if failed else "success")
        self._show_result_actions(result)
        self._warnings.value = "\n".join(result.warnings)
        self._warnings.visible = bool(result.warnings)
        self.run_btn.disabled = not self.can_run()
        self.on_result(result)
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
            # cambiarlo mientras este panel estaba oculto. `sync` no avisa, así
            # que se refresca lo que depende de él (p. ej. el nombre previsto).
            self._out_dir.sync()
            self.on_output_dir_changed()
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
        # Avisos del resultado (p. ej. páginas rasterizadas): bajo el resumen,
        # sin diálogo ni clic extra.
        self._warnings = ft.Text(
            "", size=14, color=ft.Colors.ON_SURFACE_VARIANT, visible=False
        )
        self._counter = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._error_toggle = ft.TextButton(
            t("ui.panel.show_detail"),
            visible=False,
            on_click=self._toggle_error_detail,
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
            t("ui.panel.open_folder"), icon=ft.Icons.FOLDER_OPEN, visible=False
        )
        self.open_file_btn = ft.FilledButton(
            t("ui.panel.open_file"), icon=ft.Icons.OPEN_IN_NEW, visible=False
        )
        self.run_btn = ft.FilledButton(
            t(self.run_label_key),
            icon=self.run_icon,
            disabled=True,
            tooltip=t(
                "ui.shortcut", label=t("ui.panel.execute"), keys=shortcut_label("Enter")
            ),
        )
        self.cancel_btn = ft.OutlinedButton(
            t("ui.panel.cancel"),
            icon=ft.Icons.STOP,
            visible=False,
            on_click=self._cancel_run,
        )
        self._result_actions = ft.Row(
            [self.open_file_btn, self.open_btn], visible=False, wrap=True, spacing=8
        )
        self._feedback = ft.Column(
            [
                self.progress,
                self._status_row,
                self._warnings,
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

        self.run_btn.on_click = self._on_run_click
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
        self._file_label = ft.Text(t("ui.panel.no_file"), italic=True)
        self._picker.on_result = self._on_pick
        self._pick_btn = ft.FilledTonalButton(
            t(self.pick_label_key),
            icon=self.pick_icon,
            tooltip=t(
                "ui.shortcut", label=t(self.pick_label_key), keys=shortcut_label("O")
            ),
            on_click=lambda _e: self._picker.pick_files(
                allow_multiple=False,
                allowed_extensions=list(self.allowed_extensions),
            ),
        )
        return ft.Row([self._pick_btn, self._file_label])

    def _lock_inputs(self, locked: bool) -> None:
        self._pick_btn.disabled = locked

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
            self._set_status(t("ui.web_mode"))
            self._clear_error()
        self._page.update()

    def after_pick(self, path: Path) -> None:
        """Hook opcional tras elegir un archivo válido (p.ej. leer nº de páginas).

        Si lanza, la selección se descarta y el error se muestra al usuario.
        """

    def _reject_pick(self, exc: Exception) -> None:
        self._logger().warning("no se pudo leer la entrada", exc_info=exc)
        self._file = None
        self._file_label.value = t("ui.panel.no_file")
        self._file_label.italic = True
        self._sync_ready_state()
        self._set_status(humanize_error(exc)[0], "error")

    def collect_inputs(self) -> list[Path]:
        return [] if self._file is None else [self._file]

    def can_run(self) -> bool:
        return self._file is not None
