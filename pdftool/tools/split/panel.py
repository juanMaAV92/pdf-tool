from __future__ import annotations

from pathlib import Path

import fitz
import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.split.logic import parse_ranges, resolve_ranges, split
from pdftool.tools.split.params import SplitParams
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel

_RANGES_HELP = (
    "Cómo escribir rangos:\n"
    "  1-3    →  páginas 1 a la 3\n"
    "  5      →  solo la página 5\n"
    "  8-     →  de la página 8 hasta el final\n"
    "  -4     →  del inicio hasta la página 4\n"
    "Separa varios rangos con comas:\n"
    "  1-3, 5, 8-"
)


@register
class SplitTool(SingleFileToolPanel):
    meta = ToolMeta(
        id="split",
        name="Dividir PDF",
        description="Separa un PDF en varios, por rangos o por páginas.",
        icon=ft.Icons.CONTENT_CUT,
        category="Organizar",
    )
    run_label = "Dividir"
    run_icon = ft.Icons.CONTENT_CUT
    pick_label = "Elegir PDF"

    def extra_controls(self) -> list[ft.Control]:
        self._pages = 0
        self._ranges_field = ft.TextField(
            label="Rangos", hint_text="ej: 1-3, 5, 8-", width=240, disabled=False)
        self._every_field = ft.TextField(
            label="Cada N páginas", value="10", width=160, disabled=True,
            keyboard_type=ft.KeyboardType.NUMBER)
        self._mode = ft.RadioGroup(
            value="ranges",
            content=ft.Column([
                ft.Row([
                    ft.Radio(value="ranges", label="Por rangos"),
                    self._ranges_field,
                    ft.IconButton(ft.Icons.HELP_OUTLINE, tooltip=_RANGES_HELP),
                ]),
                ft.Radio(value="single", label="Una página por archivo"),
                ft.Row([
                    ft.Radio(value="every", label="Cada"),
                    self._every_field,
                    ft.Text("páginas"),
                ]),
            ], spacing=8),
        )
        self._mode.on_change = self._on_mode_change
        return [ft.Text("Cómo dividir:", weight=ft.FontWeight.W_500), self._mode]

    def _on_mode_change(self, _e) -> None:
        self._ranges_field.disabled = self._mode.value != "ranges"
        self._every_field.disabled = self._mode.value != "every"
        self._page.update()

    def after_pick(self, path: Path) -> None:
        with fitz.open(str(path)) as doc:
            self._pages = doc.page_count
        self._file_label.value = f"{path.name} · {self._pages} páginas"

    def make_params(self):
        try:
            params = SplitParams(
                mode=self._mode.value,
                ranges=self._ranges_field.value or "",
                every_n=int(self._every_field.value) if self._every_field.value else 1,
            )
            if params.mode == "ranges":
                # Valida sintaxis y límites antes de lanzar el job.
                resolve_ranges(parse_ranges(params.ranges), int(self._pages))
        except ValueError as exc:
            raise InvalidParams(str(exc))
        except Exception:  # noqa: BLE001  (pydantic/int inválido)
            raise InvalidParams("Parámetros inválidos")
        return params

    def run_logic(self, inputs: list[Path], params, progress):
        return split(inputs, params, progress=progress)
