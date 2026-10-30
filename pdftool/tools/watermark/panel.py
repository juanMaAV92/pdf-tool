from __future__ import annotations

import flet as ft
from pydantic import ValidationError

from pdftool.tools.watermark.params import WatermarkParams
from pdftool.tools.watermark.spec import SPEC
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register

_COLORS = {
    "Gris": (0.5, 0.5, 0.5),
    "Rojo": (0.85, 0.2, 0.2),
    "Azul": (0.2, 0.4, 0.85),
    "Negro": (0.0, 0.0, 0.0),
}


@register
class WatermarkTool(SingleFileToolPanel):
    spec = SPEC
    icon = ft.Icons.BRANDING_WATERMARK
    run_label = "Añadir marca de agua"
    run_icon = ft.Icons.BRANDING_WATERMARK
    pick_label = "Elegir PDF"

    def extra_controls(self) -> list[ft.Control]:
        self._text_field = ft.TextField(
            label="Texto de la marca", value="CONFIDENCIAL", width=320
        )
        # En porcentaje: «15 %» se entiende mejor que «0.15».
        self._opacity = ft.Slider(
            min=5,
            max=60,
            value=15,
            divisions=11,
            label="{value} %",
            width=320,
        )
        self._color_dd = ft.Dropdown(
            label="Color",
            width=160,
            value="Gris",
            options=[ft.dropdown.Option(name) for name in _COLORS],
        )
        self._size_field = ft.TextField(
            label="Tamaño del texto (pt)",
            value="40",
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        return [
            self._text_field,
            ft.Row([self._color_dd, self._size_field]),
            ft.Column([ft.Text("Opacidad"), self._opacity], spacing=0),
        ]

    def make_params(self):
        try:
            return WatermarkParams(
                text=self._text_field.value or "",
                opacity=float(self._opacity.value) / 100,
                font_size=int(self._size_field.value),
                color=_COLORS.get(self._color_dd.value, _COLORS["Gris"]),
            )
        except (ValueError, ValidationError) as exc:
            raise InvalidParams("Revisa el texto, tamaño y opacidad.") from exc
