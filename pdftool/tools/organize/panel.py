from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.errors import UserError
from pdftool.core.pages import parse_plan
from pdftool.i18n import t
from pdftool.tools.organize.logic import read_page_count
from pdftool.tools.organize.params import OrganizeParams
from pdftool.tools.organize.spec import SPEC
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register


@register
class OrganizeTool(SingleFileToolPanel):
    spec = SPEC
    icon = ft.Icons.DASHBOARD_CUSTOMIZE
    run_label_key = "tool.organize.ui.run"
    run_icon = ft.Icons.SAVE
    pick_label_key = "ui.panel.pick_pdf"

    def extra_controls(self) -> list[ft.Control]:
        self._pages = 0
        self._plan_field = ft.TextField(
            label=t("tool.organize.ui.plan"),
            hint_text=t("tool.organize.ui.plan_hint"),
            width=320,
        )
        return [self._plan_field]

    def after_pick(self, path: Path) -> None:
        # Se reinicia antes de leer: si el PDF no abre, el plan no debe
        # validarse contra las páginas del archivo anterior.
        self._pages = 0
        self._file_label.value = t("tool.organize.ui.reading", name=path.name)

        def on_done(count: int) -> None:
            if self._file != path:  # el usuario ya eligió otro archivo
                return
            self._pages = count
            self._file_label.value = t(
                "tool.organize.ui.pages", name=path.name, count=count
            )
            self._sync_ready_state()
            self._page.update()

        def on_error(exc: Exception) -> None:
            if self._file != path:
                return
            self._reject_pick(exc)
            self._page.update()

        self._ctx.run_job(
            work=lambda _progress: read_page_count(path),
            on_progress=lambda *_: None,
            on_done=on_done,
            on_error=on_error,
        )

    def can_run(self) -> bool:
        return super().can_run() and self._pages > 0

    def make_params(self):
        pages = self._plan_field.value or ""
        try:
            parse_plan(pages, self._pages)
        except UserError as exc:
            raise InvalidParams(str(exc), field=self._plan_field) from exc
        return OrganizeParams(pages=pages)
