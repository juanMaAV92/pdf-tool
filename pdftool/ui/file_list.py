from __future__ import annotations

import base64
from pathlib import Path

import flet as ft

from pdftool.core.plugin import ToolResult
from pdftool.core.thumbnails import THUMBNAIL_HEIGHT_PX
from pdftool.ui.panel_base import _WEB_MODE_MSG, BaseToolPanel
from pdftool.ui.platform import open_file
from pdftool.ui.thumbnails import MISSING, get_cached, load_async


class MultiFileToolPanel(BaseToolPanel):
    """Panel de lotes con lista, orden, resultados y miniaturas opcionales."""

    min_files: int = 1
    show_thumbnails: bool = False  # solo tools donde el orden/identidad importa

    def build_input(self, page) -> ft.Control:
        previous_task = getattr(self, "_thumb_task", None)
        if previous_task is not None:
            previous_task.cancel()
        self._files: list[Path] = []
        self._results: list[str] = []  # etiqueta por archivo tras un run
        self._row_paths: list[Path | None] = []  # ruta por fila exitosa tras un run
        self._thumb_boxes: dict[str, ft.Container] = {}
        self._thumb_task = None
        self._thumb_generation = getattr(self, "_thumb_generation", -1) + 1
        self._picker.on_result = self._on_pick
        self._clear_btn = ft.OutlinedButton(
            "Limpiar lista",
            icon=ft.Icons.CLEAR_ALL,
            disabled=True,
            on_click=self._clear_all,
        )
        return ft.Row(
            [
                ft.FilledTonalButton(
                    self.pick_label,
                    icon=self.pick_icon,
                    on_click=lambda _e: self._picker.pick_files(
                        allow_multiple=True, allowed_extensions=self.allowed_extensions
                    ),
                ),
                self._clear_btn,
            ]
        )

    def build_body(self) -> ft.Control:
        # La lista rellena el cuerpo y scrollea sola cuando no cabe; el footer
        # (ejecutar, progreso, status) queda siempre visible.
        self._file_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        return self._file_list

    @staticmethod
    def _thumb_image(png: bytes) -> ft.Image:
        return ft.Image(
            src_base64=base64.b64encode(png).decode(),
            height=THUMBNAIL_HEIGHT_PX,
            fit=ft.ImageFit.CONTAIN,
        )

    def _thumb_control(self, path: Path) -> ft.Container:
        cached = get_cached(path)
        if cached is not MISSING and cached is not None:
            content: ft.Control = self._thumb_image(cached)
        else:
            icon = (
                ft.Icons.PICTURE_AS_PDF
                if path.suffix.lower() == ".pdf"
                else ft.Icons.IMAGE
            )
            content = ft.Icon(icon, size=28, color=ft.Colors.ON_SURFACE_VARIANT)
        box = ft.Container(
            content=content,
            height=THUMBNAIL_HEIGHT_PX,
            width=44,
            alignment=ft.alignment.center,
        )
        self._thumb_boxes[str(path)] = box
        return box

    def _on_thumb_ready(self, path: Path, png: bytes | None) -> None:
        # Llega desde el hilo del loader; si la fila ya no existe o el render
        # falló (None), el placeholder/icono se queda como está.
        box = self._thumb_boxes.get(str(path))
        if box is None or png is None:
            return
        box.content = self._thumb_image(png)
        self._page.update()

    def _refresh(self) -> None:
        if self._thumb_task is not None:
            self._thumb_task.cancel()
            self._thumb_task = None
        self._thumb_generation += 1
        generation = self._thumb_generation
        self._thumb_boxes = {}
        self._file_list.controls.clear()
        for index, path in enumerate(self._files):
            result = self._results[index] if index < len(self._results) else None
            row_path = self._row_paths[index] if index < len(self._row_paths) else None
            controls: list[ft.Control] = [ft.Text(f"{index + 1}.", width=28)]
            if self.show_thumbnails:
                controls.append(self._thumb_control(path))
            controls += [
                ft.Text(path.name, expand=True, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(
                    result or "",
                    size=12,
                    no_wrap=True,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.IconButton(
                    ft.Icons.OPEN_IN_NEW,
                    tooltip="Abrir",
                    visible=row_path is not None,
                    on_click=lambda _e, p=row_path: open_file(p),
                ),
                ft.IconButton(
                    ft.Icons.ARROW_UPWARD,
                    tooltip="Subir",
                    disabled=index == 0,
                    on_click=lambda _e, i=index: self._move(i, -1),
                ),
                ft.IconButton(
                    ft.Icons.ARROW_DOWNWARD,
                    tooltip="Bajar",
                    disabled=index == len(self._files) - 1,
                    on_click=lambda _e, i=index: self._move(i, 1),
                ),
                ft.IconButton(
                    ft.Icons.CLOSE,
                    tooltip="Quitar",
                    on_click=lambda _e, i=index: self._remove(i),
                ),
            ]
            self._file_list.controls.append(
                ft.Row(controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            )
        if self.show_thumbnails:
            pending = [p for p in self._files if get_cached(p) is MISSING]
            if pending:
                self._thumb_task = load_async(
                    pending,
                    self._on_thumb_ready,
                    is_current=lambda: self._thumb_generation == generation,
                )
        self.on_inputs_changed()
        self._sync_ready_state()
        self._clear_btn.disabled = not self._files
        n = len(self._files)
        self._counter.value = (
            "" if n == 0 else "1 archivo" if n == 1 else f"{n} archivos"
        )
        self._page.update()

    def _clear_results(self) -> None:
        self._results = []
        self._row_paths = []

    def _move(self, index: int, delta: int) -> None:
        new_index = index + delta
        if 0 <= new_index < len(self._files):
            self._invalidate_active_job()
            self._files[index], self._files[new_index] = (
                self._files[new_index],
                self._files[index],
            )
            self._clear_results()
            self._refresh()

    def _remove(self, index: int) -> None:
        self._invalidate_active_job()
        self._files.pop(index)
        self._clear_results()
        self._refresh()

    def _clear_all(self, _e) -> None:
        self._invalidate_active_job()
        self._files = []
        self._clear_results()
        self._clear_error()
        self.status.value = ""
        self._hide_result_actions()
        self._refresh()

    def _on_pick(self, e) -> None:
        if not e.files:
            return
        self._invalidate_active_job()
        added = 0
        for f in e.files:
            if not f.path:  # navegador (modo web): sin ruta local
                continue
            path = Path(f.path)
            if path not in self._files:
                self._files.append(path)
                added += 1
        if added == 0 and e.files:
            self.status.value = _WEB_MODE_MSG
        else:
            self._hide_result_actions()
            self.status.value = ""
        self._clear_error()
        self._clear_results()
        self._refresh()

    def on_result(self, result: ToolResult) -> None:
        items = result.items or []
        self._results = [item.message for item in items]
        self._row_paths = [item.output_path if item.ok else None for item in items]
        self._refresh()

    def collect_inputs(self) -> list[Path]:
        return list(self._files)

    def can_run(self) -> bool:
        return len(self._files) >= self.min_files
