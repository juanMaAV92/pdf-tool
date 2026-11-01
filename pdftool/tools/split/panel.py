from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.errors import UserError
from pdftool.i18n import t
from pdftool.tools.split.logic import page_count, parse_ranges, resolve_ranges
from pdftool.tools.split.params import SplitParams
from pdftool.tools.split.spec import SPEC
from pdftool.ui.accessibility import HelpButton
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register


@register
class SplitTool(SingleFileToolPanel):
    spec = SPEC
    icon = ft.Icons.CONTENT_CUT
    run_label_key = "tool.split.ui.run"
    run_icon = ft.Icons.CONTENT_CUT
    pick_label_key = "ui.panel.pick_pdf"

    def extra_controls(self) -> list[ft.Control]:
        self._pages = 0
        self._ranges_help = HelpButton(
            t("tool.split.ui.help_title"), t("tool.split.ui.help")
        )
        self._ranges_field = ft.TextField(
            label=t("tool.split.ui.ranges"),
            hint_text=t("tool.split.ui.ranges_hint"),
            width=240,
            disabled=False,
        )
        # Sin label propio: la fila ya se lee «Cada [10] páginas».
        self._every_field = ft.TextField(
            value="10",
            tooltip=t("tool.split.ui.pages_per_file"),
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
                            ft.Radio(
                                value="ranges", label=t("tool.split.ui.mode.ranges")
                            ),
                            self._ranges_field,
                            self._ranges_help,
                        ]
                    ),
                    self._ranges_help.detail,
                    ft.Radio(value="single", label=t("tool.split.ui.mode.single")),
                    ft.Row(
                        [
                            ft.Radio(
                                value="every", label=t("tool.split.ui.mode.every")
                            ),
                            self._every_field,
                            ft.Text(t("tool.split.ui.mode.every_unit")),
                        ]
                    ),
                ],
                spacing=8,
            ),
        )
        self._mode.on_change = self._on_mode_change
        return [ft.Text(t("tool.split.ui.how"), weight=ft.FontWeight.W_500), self._mode]

    def _on_mode_change(self, _e) -> None:
        self._ranges_field.disabled = self._mode.value != "ranges"
        self._every_field.disabled = self._mode.value != "every"
        self._page.update()

    def after_pick(self, path: Path) -> None:
        # Se reinicia antes de leer: si el PDF no abre, los rangos no deben
        # validarse contra las páginas del archivo anterior.
        self._pages = 0
        self._file_label.value = t("tool.split.ui.reading", name=path.name)

        # Abrir un PDF grande o dañado puede tardar: se lee en segundo plano.
        def on_done(count: int) -> None:
            if self._file != path:  # el usuario ya eligió otro archivo
                return
            self._pages = count
            self._file_label.value = t(
                "tool.split.ui.pages", name=path.name, count=count
            )
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
                t("tool.split.ui.error.every"), field=self._every_field
            ) from exc
        if params.mode == "ranges":
            # Valida sintaxis y límites antes de lanzar el job.
            try:
                resolve_ranges(parse_ranges(params.ranges), int(self._pages))
            except UserError as exc:
                raise InvalidParams(str(exc), field=self._ranges_field) from exc
        return params
