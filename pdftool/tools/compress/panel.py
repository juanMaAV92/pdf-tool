from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.compress.logic import compress
from pdftool.tools.compress.params import CompressParams
from pdftool.ui.accessibility import HelpButton
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import InvalidParams

_MODE_HELP = (
    "Reducir al máximo: busca el archivo más pequeño posible. Algunas páginas "
    "pueden dejar de tener texto seleccionable.\n\n"
    "Conservar texto y enlaces: mantiene búsqueda, copiar/pegar, enlaces y "
    "anotaciones cuando sea posible, aunque el archivo puede pesar más."
)


@register
class CompressTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="compress",
        name="Comprimir PDF",
        description="Reduce el tamaño de uno o varios PDFs a un objetivo en MB.",
        icon=ft.Icons.COMPRESS,
        category="Optimizar",
        order=30,
    )
    run_label = "Comprimir"
    run_icon = ft.Icons.PLAY_ARROW
    pick_label = "Añadir PDFs"
    min_files = 1

    def extra_controls(self) -> list[ft.Control]:
        self._target_field = ft.TextField(
            label="Tamaño objetivo (MB)",
            value="5",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
            helper_text="Objetivo, no garantía.",
        )
        self._mode_dd = ft.Dropdown(
            label="Modo de compresión",
            width=260,
            value="max",
            options=[
                ft.dropdown.Option("max", "Reducir al máximo (recomendado)"),
                ft.dropdown.Option("preserve", "Conservar texto y enlaces"),
            ],
        )
        self._mode_help = HelpButton("Ayuda sobre compresión", _MODE_HELP)
        return [
            ft.Row(
                [
                    self._target_field,
                    self._mode_dd,
                    self._mode_help,
                ],
                spacing=12,
            ),
            self._mode_help.detail,
        ]

    def make_params(self):
        # En español se escribe «2,5»: se acepta la coma decimal.
        text = (self._target_field.value or "").strip().replace(",", ".")
        try:
            return CompressParams(target_mb=float(text), mode=self._mode_dd.value)
        except (ValueError, ValidationError) as exc:
            raise InvalidParams(
                "Escribe un tamaño mayor que 0, por ejemplo 5 o 2,5.",
                field=self._target_field,
            ) from exc

    def run_logic(self, inputs: list[Path], params, progress):
        return compress(inputs, params, progress=progress)
