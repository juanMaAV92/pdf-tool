from __future__ import annotations

from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.watermark.logic import watermark
from pdftool.tools.watermark.params import WatermarkParams
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel

_COLORS = {
    "Gris": (0.5, 0.5, 0.5),
    "Rojo": (0.85, 0.2, 0.2),
    "Azul": (0.2, 0.4, 0.85),
    "Negro": (0.0, 0.0, 0.0),
}


@register
class WatermarkTool(SingleFileToolPanel):
    meta = ToolMeta(
        id="watermark",
        name="Marca de agua",
        description="Repite un texto en diagonal sobre todas las páginas.",
        icon=ft.Icons.BRANDING_WATERMARK,
        category="Editar",
    )
    run_label = "Aplicar"
    run_icon = ft.Icons.BRANDING_WATERMARK
    pick_label = "Elegir PDF"

    def extra_controls(self) -> list[ft.Control]:
        self._text_field = ft.TextField(label="Texto de la marca", value="CONFIDENCIAL",
                                         width=320)
        self._opacity = ft.Slider(min=0.05, max=0.6, value=0.15, divisions=11,
                                  label="{value}", round=2, width=320)
        self._color_dd = ft.Dropdown(
            label="Color", width=160, value="Gris",
            options=[ft.dropdown.Option(name) for name in _COLORS],
        )
        self._size_field = ft.TextField(label="Tamaño", value="40", width=120,
                                        keyboard_type=ft.KeyboardType.NUMBER)
        return [
            self._text_field,
            ft.Row([self._color_dd, self._size_field]),
            ft.Column([ft.Text("Opacidad"), self._opacity], spacing=0),
        ]

    def make_params(self):
        try:
            return WatermarkParams(
                text=self._text_field.value or "",
                opacity=float(self._opacity.value),
                font_size=int(self._size_field.value),
                color=_COLORS.get(self._color_dd.value, _COLORS["Gris"]),
            )
        except (ValueError, ValidationError):
            raise InvalidParams("Revisa el texto, tamaño y opacidad.")

    def run_logic(self, inputs: list[Path], params, progress):
        return watermark(inputs, params, progress=progress)
