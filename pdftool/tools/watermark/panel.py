from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta
from pdftool.core.registry import register
from pdftool.tools.watermark.logic import watermark
from pdftool.tools.watermark.params import WatermarkParams

_COLORS = {
    "Gris": (0.5, 0.5, 0.5),
    "Rojo": (0.85, 0.2, 0.2),
    "Azul": (0.2, 0.4, 0.85),
    "Negro": (0.0, 0.0, 0.0),
}


def _open_folder(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


@register
class WatermarkTool(PdfTool):
    meta = ToolMeta(
        id="watermark",
        name="Marca de agua",
        description="Repite un texto en diagonal sobre todas las páginas.",
        icon=ft.Icons.BRANDING_WATERMARK,
        category="Editar",
    )

    def __init__(self) -> None:
        self._picker = ft.FilePicker()

    def build_panel(self, ctx: ToolContext) -> ft.Control:
        page: ft.Page = ctx.page
        selected: dict[str, Path | None] = {"file": None}

        file_label = ft.Text("Ningún archivo seleccionado", italic=True)
        text_field = ft.TextField(label="Texto de la marca", value="CONFIDENCIAL",
                                   width=320)
        opacity = ft.Slider(min=0.05, max=0.6, value=0.15, divisions=11,
                            label="{value}", width=320)
        color_dd = ft.Dropdown(
            label="Color", width=160, value="Gris",
            options=[ft.dropdown.Option(name) for name in _COLORS],
        )
        size_field = ft.TextField(label="Tamaño", value="40", width=120,
                                   keyboard_type=ft.KeyboardType.NUMBER)
        progress = ft.ProgressBar(value=0, visible=False)
        status = ft.Text("")
        run_btn = ft.FilledButton("Aplicar", icon=ft.Icons.BRANDING_WATERMARK,
                                  disabled=True)
        open_btn = ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                     visible=False)

        def on_pick(e: ft.FilePickerResultEvent) -> None:
            if e.files and e.files[0].path:
                selected["file"] = Path(e.files[0].path)
                file_label.value = selected["file"].name
                file_label.italic = False
                run_btn.disabled = False
                open_btn.visible = False
                status.value = ""
                page.update()
            elif e.files:
                status.value = "El modo navegador no da rutas locales; usa la app de escritorio."
                page.update()

        self._picker.on_result = on_pick
        if self._picker not in page.overlay:
            page.overlay.append(self._picker)

        def set_progress(pct: float, msg: str) -> None:
            progress.value = pct
            status.value = msg
            page.update()

        def on_done(result) -> None:
            progress.visible = False
            status.value = result.summary
            open_btn.visible = True
            open_btn.data = result.outputs[0].parent
            run_btn.disabled = False
            page.update()

        def on_error(exc: Exception) -> None:
            progress.visible = False
            status.value = f"Error: {exc}"
            run_btn.disabled = False
            page.update()

        def do_run(_e) -> None:
            if not selected["file"]:
                return
            try:
                params = WatermarkParams(
                    text=text_field.value or "",
                    opacity=float(opacity.value),
                    font_size=int(size_field.value),
                    color=_COLORS.get(color_dd.value, _COLORS["Gris"]),
                )
            except (ValueError, ValidationError):
                status.value = "Revisa el texto, tamaño y opacidad."
                page.update()
                return
            run_btn.disabled = True
            open_btn.visible = False
            progress.visible = True
            progress.value = 0
            page.update()
            ctx.run_job(
                work=lambda prog: watermark([selected["file"]], params, progress=prog),
                on_progress=set_progress,
                on_done=on_done,
                on_error=on_error,
            )

        run_btn.on_click = do_run
        open_btn.on_click = lambda _e: _open_folder(Path(open_btn.data))

        return ft.Column(
            [
                ft.Text(self.meta.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(self.meta.description),
                ft.Divider(),
                ft.Row([
                    ft.FilledTonalButton(
                        "Elegir PDF", icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda _e: self._picker.pick_files(
                            allow_multiple=False, allowed_extensions=["pdf"])),
                    file_label,
                ]),
                text_field,
                ft.Row([color_dd, size_field]),
                ft.Column([ft.Text("Opacidad"), opacity], spacing=0),
                ft.Row([run_btn, open_btn]),
                progress,
                status,
            ],
            spacing=16,
        )
