from __future__ import annotations

import flet as ft
from pydantic import ValidationError

from pdftool.tools.compress.params import CompressParams
from pdftool.tools.compress.spec import SPEC
from pdftool.ui.accessibility import HelpButton
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import InvalidParams
from pdftool.ui.registry import register

_MODE_HELP = (
    "Reducir al máximo: busca el archivo más pequeño posible. Algunas páginas "
    "pueden dejar de tener texto seleccionable.\n\n"
    "Conservar texto y enlaces: mantiene búsqueda, copiar/pegar, enlaces y "
    "anotaciones cuando sea posible, aunque el archivo puede pesar más."
)


@register
class CompressTool(MultiFileToolPanel):
    spec = SPEC
    icon = ft.Icons.COMPRESS
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
            width=330,  # cabe «Reducir al máximo (recomendado)» sin recortarse
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
                wrap=True,  # en ventanas estrechas pasa a dos líneas
                # Arriba, no centrados: la ayuda «Objetivo, no garantía.» alarga
                # el campo del objetivo y lo descuadraba frente al desplegable.
                vertical_alignment=ft.CrossAxisAlignment.START,
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
