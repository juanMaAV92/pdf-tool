from __future__ import annotations

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import ToolResult
from pdftool.i18n import t
from pdftool.tools.protect.params import ProtectParams
from pdftool.tools.protect.spec import SPEC
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import InvalidParams
from pdftool.ui.registry import register


@register
class ProtectTool(MultiFileToolPanel):
    spec = SPEC
    icon = ft.Icons.LOCK
    run_label_key = "tool.protect.ui.run"
    run_icon = ft.Icons.LOCK
    pick_label_key = "ui.panel.add_pdfs"

    def extra_controls(self) -> list[ft.Control]:
        self._mode_dd = ft.Dropdown(
            label=t("tool.protect.ui.action"),
            width=240,
            value="protect",
            options=[
                ft.dropdown.Option("protect", t("tool.protect.ui.mode.protect")),
                ft.dropdown.Option("remove", t("tool.protect.ui.mode.remove")),
            ],
        )
        self._mode_dd.on_change = self._on_mode_change
        self._pw_field = ft.TextField(
            label=t("tool.protect.ui.password"),
            width=320,
            password=True,
            can_reveal_password=True,
        )
        # Un error al teclear dejaría un PDF que nadie puede abrir.
        self._confirm_field = ft.TextField(
            label=t("tool.protect.ui.confirm"),
            width=320,
            password=True,
            can_reveal_password=True,
            helper_text=t("tool.protect.ui.keep_safe"),
        )
        return [self._mode_dd, self._pw_field, self._confirm_field]

    def _on_mode_change(self, _e) -> None:
        protecting = self._mode_dd.value == "protect"
        self._pw_field.label = t(
            "tool.protect.ui.password" if protecting else "tool.protect.ui.current"
        )
        self._confirm_field.visible = protecting
        self.run_btn.text = t(
            "tool.protect.ui.run" if protecting else "tool.protect.ui.run_remove"
        )
        self.run_btn.icon = ft.Icons.LOCK if protecting else ft.Icons.LOCK_OPEN
        self._page.update()

    def on_result(self, result: ToolResult) -> None:
        super().on_result(result)
        # No dejar la contraseña escrita en un panel que se conserva al navegar.
        self._pw_field.value = ""
        self._confirm_field.value = ""

    def make_params(self):
        password = self._pw_field.value or ""
        try:
            params = ProtectParams(mode=self._mode_dd.value, password=password)
        except (ValueError, ValidationError) as exc:
            raise InvalidParams(
                t("tool.protect.ui.error.empty"), field=self._pw_field
            ) from exc
        if params.mode == "protect" and password != (self._confirm_field.value or ""):
            raise InvalidParams(
                t("tool.protect.ui.error.mismatch"), field=self._confirm_field
            )
        return params
