from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.protect.logic import protect
from pdftool.tools.protect.params import ProtectParams
from pdftool.ui.panel_base import InvalidParams, MultiFileToolPanel


@register
class ProtectTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="protect",
        name="Proteger PDF",
        description="Añade o quita la contraseña de uno o varios PDFs.",
        icon=ft.Icons.LOCK,
        category="Seguridad",
    )
    run_label = "Aplicar"
    run_icon = ft.Icons.LOCK
    pick_label = "Añadir PDFs"
    min_files = 1

    def extra_controls(self) -> list[ft.Control]:
        self._mode_dd = ft.Dropdown(
            label="Acción", width=240, value="protect",
            options=[
                ft.dropdown.Option("protect", "Proteger (poner contraseña)"),
                ft.dropdown.Option("remove", "Quitar contraseña"),
            ],
        )
        self._pw_field = ft.TextField(label="Contraseña", width=320, password=True,
                                      can_reveal_password=True)
        return [self._mode_dd, self._pw_field]

    def make_params(self):
        try:
            return ProtectParams(mode=self._mode_dd.value,
                                 password=self._pw_field.value or "")
        except (ValueError, ValidationError):
            raise InvalidParams("Escribe una contraseña.")

    def run_logic(self, inputs: list[Path], params, progress):
        return protect(inputs, params, progress=progress)
