from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.protect.logic import protect
from pdftool.tools.protect.params import ProtectParams
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import InvalidParams


@register
class ProtectTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="protect",
        name="Proteger PDF",
        description="Añade o quita la contraseña de uno o varios PDFs.",
        icon=ft.Icons.LOCK,
        category="Seguridad",
    )
    run_label = "Proteger"
    run_icon = ft.Icons.LOCK
    pick_label = "Añadir PDFs"
    min_files = 1

    def extra_controls(self) -> list[ft.Control]:
        self._mode_dd = ft.Dropdown(
            label="Acción",
            width=240,
            value="protect",
            options=[
                ft.dropdown.Option("protect", "Proteger (poner contraseña)"),
                ft.dropdown.Option("remove", "Quitar contraseña"),
            ],
        )
        self._mode_dd.on_change = self._on_mode_change
        self._pw_field = ft.TextField(
            label="Contraseña", width=320, password=True, can_reveal_password=True
        )
        # Un error al teclear dejaría un PDF que nadie puede abrir.
        self._confirm_field = ft.TextField(
            label="Repetir contraseña",
            width=320,
            password=True,
            can_reveal_password=True,
            helper_text="Guárdala bien: sin ella no podrás abrir el PDF.",
        )
        return [self._mode_dd, self._pw_field, self._confirm_field]

    def _on_mode_change(self, _e) -> None:
        protecting = self._mode_dd.value == "protect"
        self._pw_field.label = "Contraseña" if protecting else "Contraseña actual"
        self._confirm_field.visible = protecting
        self.run_btn.text = "Proteger" if protecting else "Quitar contraseña"
        self.run_btn.icon = ft.Icons.LOCK if protecting else ft.Icons.LOCK_OPEN
        self._page.update()

    def make_params(self):
        password = self._pw_field.value or ""
        try:
            params = ProtectParams(mode=self._mode_dd.value, password=password)
        except (ValueError, ValidationError) as exc:
            raise InvalidParams("Escribe una contraseña.") from exc
        if params.mode == "protect" and password != (self._confirm_field.value or ""):
            raise InvalidParams("Las contraseñas no coinciden.")
        return params

    def run_logic(self, inputs: list[Path], params, progress):
        return protect(inputs, params, progress=progress)
