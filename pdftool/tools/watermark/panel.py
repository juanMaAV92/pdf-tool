from __future__ import annotations

import flet as ft
from pydantic import ValidationError

from pdftool.i18n import t
from pdftool.tools.watermark.params import WatermarkParams
from pdftool.tools.watermark.spec import SPEC
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register

# Ids estables; el nombre visible sale de `tool.watermark.color.<id>`.
_COLORS = {
    "gray": (0.5, 0.5, 0.5),
    "red": (0.85, 0.2, 0.2),
    "blue": (0.2, 0.4, 0.85),
    "black": (0.0, 0.0, 0.0),
}


@register
class WatermarkTool(SingleFileToolPanel):
    spec = SPEC
    icon = ft.Icons.BRANDING_WATERMARK
    run_label_key = "tool.watermark.ui.run"
    run_icon = ft.Icons.BRANDING_WATERMARK
    pick_label_key = "ui.panel.pick_pdf"

    def extra_controls(self) -> list[ft.Control]:
        self._text_field = ft.TextField(
            label=t("tool.watermark.ui.text"),
            value=t("tool.watermark.ui.default_text"),
            width=320,
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
            label=t("tool.watermark.ui.color"),
            width=160,
            value="gray",
            options=[
                ft.dropdown.Option(key=cid, text=t(f"tool.watermark.color.{cid}"))
                for cid in _COLORS
            ],
        )
        self._size_field = ft.TextField(
            label=t("tool.watermark.ui.size"),
            value="40",
            width=180,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        return [
            self._text_field,
            ft.Row([self._color_dd, self._size_field]),
            ft.Column(
                [ft.Text(t("tool.watermark.ui.opacity")), self._opacity], spacing=0
            ),
        ]

    def make_params(self):
        try:
            return WatermarkParams(
                text=self._text_field.value or "",
                opacity=float(self._opacity.value) / 100,
                font_size=int(self._size_field.value),
                color=_COLORS.get(self._color_dd.value or "gray", _COLORS["gray"]),
            )
        except (ValueError, ValidationError) as exc:
            raise InvalidParams(t("tool.watermark.ui.error.params")) from exc
