from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.errors import UserError
from pdftool.core.plugin import ToolMeta
from pdftool.tools.split.logic import page_count, parse_ranges, resolve_ranges, split
from pdftool.tools.split.params import SplitParams
from pdftool.ui.accessibility import HelpButton
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register

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
        category="Organizar",
        order=20,
    )
    icon = ft.Icons.CONTENT_CUT
    logic = staticmethod(split)
    run_label = "Dividir"
    run_icon = ft.Icons.CONTENT_CUT
    pick_label = "Elegir PDF"

    def extra_controls(self) -> list[ft.Control]:
        self._pages = 0
        self._ranges_help = HelpButton("Ayuda sobre rangos de páginas", _RANGES_HELP)
        self._ranges_field = ft.TextField(
            label="Rangos", hint_text="ej: 1-3, 5, 8-", width=240, disabled=False
        )
        # Sin label propio: la fila ya se lee «Cada [10] páginas».
        self._every_field = ft.TextField(
            value="10",
            tooltip="Páginas por archivo",
            width=160,
            disabled=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self._mode = ft.RadioGroup(
            value="ranges",
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Radio(value="ranges", label="Por rangos"),
                            self._ranges_field,
                            self._ranges_help,
                        ]
                    ),
                    self._ranges_help.detail,
                    ft.Radio(value="single", label="Una página por archivo"),
                    ft.Row(
                        [
                            ft.Radio(value="every", label="Cada"),
                            self._every_field,
                            ft.Text("páginas"),
                        ]
                    ),
                ],
                spacing=8,
            ),
        )
        self._mode.on_change = self._on_mode_change
        return [ft.Text("Cómo dividir:", weight=ft.FontWeight.W_500), self._mode]

    def _on_mode_change(self, _e) -> None:
        self._ranges_field.disabled = self._mode.value != "ranges"
        self._every_field.disabled = self._mode.value != "every"
        self._page.update()

    def after_pick(self, path: Path) -> None:
        # Se reinicia antes de leer: si el PDF no abre, los rangos no deben
        # validarse contra las páginas del archivo anterior.
        self._pages = 0
        self._file_label.value = f"{path.name} · leyendo páginas…"

        # Abrir un PDF grande o dañado puede tardar: se lee en segundo plano.
        def on_done(count: int) -> None:
            if self._file != path:  # el usuario ya eligió otro archivo
                return
            self._pages = count
            self._file_label.value = f"{path.name} · {count} páginas"
            self._sync_ready_state()
            self._page.update()

        def on_error(exc: Exception) -> None:
            if self._file != path:
                return
            self._reject_pick(exc)
            self._page.update()

        self._ctx.run_job(
            work=lambda _progress: page_count(path),
            on_progress=lambda *_: None,
            on_done=on_done,
            on_error=on_error,
        )

    def can_run(self) -> bool:
        return super().can_run() and self._pages > 0

    def make_params(self):
        try:
            params = SplitParams(
                mode=self._mode.value,
                ranges=self._ranges_field.value or "",
                every_n=int(self._every_field.value) if self._every_field.value else 1,
            )
        except (ValueError, ValidationError) as exc:
            raise InvalidParams(
                "Escribe un número de páginas mayor que 0.", field=self._every_field
            ) from exc
        if params.mode == "ranges":
            # Valida sintaxis y límites antes de lanzar el job.
            try:
                resolve_ranges(parse_ranges(params.ranges), int(self._pages))
            except UserError as exc:
                raise InvalidParams(str(exc), field=self._ranges_field) from exc
        return params
