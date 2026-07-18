from __future__ import annotations

import logging
import time
from pathlib import Path

import flet as ft

from pdftool.core.plugin import PdfTool, ToolContext, ToolResult
from pdftool.ui.errors import humanize_error
from pdftool.ui.logs import download_log_button, make_log_picker
from pdftool.ui.platform import open_folder

_WEB_MODE_MSG = "El modo navegador no da rutas locales; usa la app de escritorio."


class InvalidParams(Exception):
    """Params inválidos; el panel muestra str(exc) en el status."""


_FORBIDDEN_NAME_CHARS = set("/\\:\x00")


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
        raise InvalidParams("Nombre de salida inválido: no puede contener / \\ :")
    return name


def output_name_field() -> ft.TextField:
    """Campo compacto y opcional para la base del archivo de salida."""
    return ft.TextField(hint_text="Nombre de salida (opcional)", width=280,
                        dense=True)


class BaseToolPanel(PdfTool):
    # Rellenados por cada herramienta:
    run_label: str = "Aplicar"
    run_icon = ft.Icons.PLAY_ARROW
    pick_label: str = "Elegir PDF"
    pick_icon = ft.Icons.UPLOAD_FILE
    allowed_extensions: list[str] = ["pdf"]

    def __init__(self) -> None:
        super().__init__()
        # Un único FilePicker reutilizado entre renders (evita fugas en overlay).
        self._picker = ft.FilePicker()
        self._log_picker = make_log_picker()  # ídem, para "Descargar log"

    # ---- hooks de la herramienta ----
    def extra_controls(self) -> list[ft.Control]:
        return []

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

    # ---- registro (log de diagnóstico; sin datos del usuario) ----
    def _logger(self) -> logging.Logger:
        return logging.getLogger(f"pdftool.{self.meta.id}")

    def _elapsed(self) -> float:
        started = getattr(self, "_run_started", None)
        return 0.0 if started is None else time.monotonic() - started

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
        self._error_toggle.text = ("Ocultar detalle" if self._error_detail.visible
                                   else "Ver detalle técnico")
        self._page.update()

    def _on_error(self, exc: Exception) -> None:
        self._logger().error("error · %.1fs", self._elapsed(), exc_info=exc)
        self.progress.visible = False
        message, detail = humanize_error(exc)
        self.status.value = message
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
        page = ctx.page
        self._page = page

        self.progress = ft.ProgressBar(value=0, visible=False)
        self.status = ft.Text("")
        self._counter = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._error_toggle = ft.TextButton("Ver detalle técnico", visible=False,
                                            on_click=self._toggle_error_detail)
        self._error_detail = ft.Text("", visible=False, selectable=True, size=12,
                                      color=ft.Colors.ON_SURFACE_VARIANT)
        self._log_btn = download_log_button(self._log_picker)
        self._log_btn.visible = False
        self._error_actions = ft.Row([self._error_toggle, self._log_btn], visible=False)
        self.open_btn = ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                          visible=False)
        self.run_btn = ft.FilledButton(self.run_label, icon=self.run_icon,
                                       disabled=True)

        input_bar = self.build_input(page)  # subclase; fija self._picker.on_result
        body = self.build_body()

        if self._picker not in page.overlay:
            page.overlay.append(self._picker)

        if self._log_picker not in page.overlay:
            page.overlay.append(self._log_picker)

        def set_progress(pct: float, msg: str) -> None:
            self.progress.value = pct
            self.status.value = msg
            page.update()

        def on_done(result: ToolResult) -> None:
            self._logger().info("ok · %.1fs", self._elapsed())
            self._clear_error()
            self.progress.visible = False
            self.status.value = result.summary
            self.open_btn.visible = True
            self.open_btn.data = result.outputs[0].parent
            self.run_btn.disabled = not self.can_run()
            self.on_result(result)
            page.update()

        def do_run(_e) -> None:
            if not self.can_run():
                return
            self._clear_error()
            try:
                params = self.make_params()
            except InvalidParams as exc:
                self.status.value = str(exc)
                page.update()
                return
            self.run_btn.disabled = True
            self.open_btn.visible = False
            self.progress.visible = True
            self.progress.value = 0
            page.update()
            inputs = self.collect_inputs()
            self._run_started = time.monotonic()
            self._logger().info("inicio · %d archivo(s)", len(inputs))
            ctx.run_job(
                work=lambda prog: self.run_logic(inputs, params, prog),
                on_progress=set_progress,
                on_done=on_done,
                on_error=self._on_error,
            )

        self.run_btn.on_click = do_run
        self.open_btn.on_click = lambda _e: open_folder(Path(self.open_btn.data))

        # Tres zonas: superior fija · cuerpo flexible · footer anclado.
        # `body` es el único hijo con expand=True: todo lo posterior queda
        # pegado al fondo sin importar cuántos archivos haya en la lista.
        return ft.Column(
            [
                ft.Text(self.meta.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(self.meta.description),
                ft.Divider(),
                input_bar,
                *self.extra_controls(),
                body,
                ft.Divider(),
                ft.Row([self.run_btn, self.open_btn,
                        ft.Container(expand=True), self._counter]),
                self.progress,
                self.status,
                self._error_actions,
                self._error_detail,
            ],
            spacing=16,
            expand=True,
        )


class SingleFileToolPanel(BaseToolPanel):
    def build_input(self, page) -> ft.Control:
        self._file: Path | None = None
        self._file_label = ft.Text("Ningún archivo seleccionado", italic=True)
        self._picker.on_result = self._on_pick
        return ft.Row([
            ft.FilledTonalButton(
                self.pick_label, icon=self.pick_icon,
                on_click=lambda _e: self._picker.pick_files(
                    allow_multiple=False, allowed_extensions=self.allowed_extensions)),
            self._file_label,
        ])

    def build_body(self) -> ft.Control:
        return ft.Container(expand=True)  # empuja el footer al fondo

    def _on_pick(self, e) -> None:
        if e.files and e.files[0].path:
            self._file = Path(e.files[0].path)
            self._file_label.value = self._file.name
            self._file_label.italic = False
            self.open_btn.visible = False
            self.status.value = ""
            self._clear_error()
            self.run_btn.disabled = False
            self.after_pick(self._file)
        elif e.files:
            self.status.value = _WEB_MODE_MSG
            self._clear_error()
        self._page.update()

    def after_pick(self, path: Path) -> None:
        """Hook opcional tras elegir un archivo válido (p.ej. leer nº de páginas)."""

    def collect_inputs(self) -> list[Path]:
        return [self._file]

    def can_run(self) -> bool:
        return self._file is not None


class MultiFileToolPanel(BaseToolPanel):
    min_files: int = 1

    def build_input(self, page) -> ft.Control:
        self._files: list[Path] = []
        self._results: list[str] = []  # etiqueta por archivo tras un run
        self._picker.on_result = self._on_pick
        self._clear_btn = ft.OutlinedButton(
            "Limpiar lista", icon=ft.Icons.CLEAR_ALL, disabled=True,
            on_click=self._clear_all)
        return ft.Row([
            ft.FilledTonalButton(
                self.pick_label, icon=self.pick_icon,
                on_click=lambda _e: self._picker.pick_files(
                    allow_multiple=True, allowed_extensions=self.allowed_extensions)),
            self._clear_btn,
        ])

    def build_body(self) -> ft.Control:
        # La lista rellena el cuerpo y scrollea sola cuando no cabe; el footer
        # (ejecutar, progreso, status) queda siempre visible.
        self._file_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO,
                                    expand=True)
        return self._file_list

    def _refresh(self) -> None:
        self._file_list.controls.clear()
        for index, path in enumerate(self._files):
            result = self._results[index] if index < len(self._results) else None
            self._file_list.controls.append(
                ft.Row(
                    [
                        ft.Text(f"{index + 1}.", width=28),
                        ft.Text(path.name, expand=True,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(result or "", size=12, no_wrap=True,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.IconButton(ft.Icons.ARROW_UPWARD, tooltip="Subir",
                                      disabled=index == 0,
                                      on_click=lambda _e, i=index: self._move(i, -1)),
                        ft.IconButton(ft.Icons.ARROW_DOWNWARD, tooltip="Bajar",
                                      disabled=index == len(self._files) - 1,
                                      on_click=lambda _e, i=index: self._move(i, 1)),
                        ft.IconButton(ft.Icons.CLOSE, tooltip="Quitar",
                                      on_click=lambda _e, i=index: self._remove(i)),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        self.run_btn.disabled = not self.can_run()
        self._clear_btn.disabled = not self._files
        n = len(self._files)
        self._counter.value = ("" if n == 0
                               else "1 archivo" if n == 1
                               else f"{n} archivos")
        self._page.update()

    def _clear_results(self) -> None:
        self._results = []

    def _move(self, index: int, delta: int) -> None:
        new_index = index + delta
        if 0 <= new_index < len(self._files):
            self._files[index], self._files[new_index] = (
                self._files[new_index], self._files[index])
            self._clear_results()
            self._refresh()

    def _remove(self, index: int) -> None:
        self._files.pop(index)
        self._clear_results()
        self._refresh()

    def _clear_all(self, _e) -> None:
        self._files = []
        self._clear_results()
        self._clear_error()
        self.status.value = ""
        self.open_btn.visible = False
        self._refresh()

    def _on_pick(self, e) -> None:
        if not e.files:
            return
        added = 0
        for f in e.files:
            if not f.path:  # navegador (modo web): sin ruta local
                continue
            p = Path(f.path)
            if p not in self._files:
                self._files.append(p)
                added += 1
        if added == 0 and e.files:
            self.status.value = _WEB_MODE_MSG
        else:
            self.open_btn.visible = False
            self.status.value = ""
        self._clear_error()
        self._clear_results()
        self._refresh()

    def on_result(self, result: ToolResult) -> None:
        self._results = list(result.details or [])
        self._refresh()

    def collect_inputs(self) -> list[Path]:
        return list(self._files)

    def can_run(self) -> bool:
        return len(self._files) >= self.min_files
