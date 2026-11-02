from __future__ import annotations

from pathlib import Path

import flet as ft
import pymupdf

from pdftool.core.plugin import ToolResult
from pdftool.i18n import t
from pdftool.tools.pdf2images.logic import (
    first_page_rect,
    page_pixels,
    result_folder_for,
)
from pdftool.tools.pdf2images.params import Pdf2ImagesParams
from pdftool.tools.pdf2images.spec import SPEC
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.registry import register


@register
class Pdf2ImagesTool(MultiFileToolPanel):
    spec = SPEC
    icon = ft.Icons.BURST_MODE
    run_label_key = "tool.pdf2images.ui.run"
    run_icon = ft.Icons.BURST_MODE
    pick_label_key = "ui.panel.add_pdfs"
    compact_when_ready = True

    def extra_controls(self) -> list[ft.Control]:
        self._first_page: tuple[Path, pymupdf.Rect] | None = None
        self._reading: Path | None = None
        self._format_dd = ft.Dropdown(
            label=t("tool.pdf2images.ui.format"),
            width=130,
            value="jpg",
            options=[
                ft.dropdown.Option("jpg", "JPG"),
                ft.dropdown.Option("png", "PNG"),
            ],
        )
        self._dpi_dd = ft.Dropdown(
            label=t("tool.pdf2images.ui.resolution"),
            width=260,
            value="300",
            options=[
                ft.dropdown.Option("150", t("tool.pdf2images.ui.dpi.150")),
                ft.dropdown.Option("300", t("tool.pdf2images.ui.dpi.300")),
            ],
            on_change=self._on_dpi_change,
        )
        self._pixels = ft.Text(
            visible=False, size=14, color=ft.Colors.ON_SURFACE_VARIANT
        )
        return [
            ft.Row([self._format_dd, self._dpi_dd], spacing=12, wrap=True),
            self._pixels,
        ]

    def _show_pixels(self) -> None:
        """Calcula sin renderizar: lo que se ve aquí es lo que se exporta."""
        if self._first_page is None:
            self._pixels.visible = False
            return
        path, rect = self._first_page
        width, height = page_pixels(rect, int(self._dpi_dd.value))
        self._pixels.value = t(
            "tool.pdf2images.ui.pixels", name=path.name, width=width, height=height
        )
        self._pixels.visible = True

    def _on_dpi_change(self, _e) -> None:
        self._show_pixels()
        self._page.update()

    def on_inputs_changed(self) -> None:
        first = self._files[0] if self._files else None
        if first is None:
            self._first_page = None
            self._reading = None
            self._show_pixels()
            return
        if self._first_page is not None and self._first_page[0] == first:
            return
        if self._reading == first:
            return
        self._first_page = None
        self._reading = first
        self._show_pixels()

        # Abrir un PDF grande o dañado puede tardar: se lee en segundo plano.
        def on_done(rect: pymupdf.Rect) -> None:
            if self._reading != first:  # la lista cambió mientras tanto
                return
            self._reading = None
            self._first_page = (first, rect)
            self._show_pixels()
            self._page.update()

        def on_error(_exc: Exception) -> None:
            # Sin línea de píxeles: el error real se ve al exportar, en su fila.
            if self._reading == first:
                self._reading = None

        self._ctx.run_job(
            work=lambda _progress: first_page_rect(first),
            on_progress=lambda *_: None,
            on_done=on_done,
            on_error=on_error,
        )

    def result_folder(self, result: ToolResult) -> Path:
        folders = [
            item.output_path
            for item in result.items or []
            if item.ok and item.output_path is not None
        ]
        return result_folder_for(folders)

    def make_params(self):
        return Pdf2ImagesParams(
            format=self._format_dd.value, dpi=int(self._dpi_dd.value)
        )
