from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import flet as ft
from pydantic import ValidationError

from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta
from pdftool.core.registry import register
from pdftool.tools.compress.logic import compress
from pdftool.tools.compress.params import CompressParams


def _open_folder(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


@register
class CompressTool(PdfTool):
    meta = ToolMeta(
        id="compress",
        name="Comprimir PDF",
        description="Reduce el tamaño de un PDF a un objetivo en MB.",
        icon=ft.Icons.COMPRESS,
        category="Optimizar",
    )

    def __init__(self) -> None:
        super().__init__()
        # Created once per tool instance to avoid leaking pickers into page.overlay.
        self._picker = ft.FilePicker()

    def build_panel(self, ctx: ToolContext) -> ft.Control:
        page: ft.Page = ctx.page
        selected: dict[str, Path | None] = {"file": None}

        file_label = ft.Text("Ningún archivo seleccionado", italic=True)
        target_field = ft.TextField(label="Tamaño objetivo (MB)", value="5",
                                     width=200, keyboard_type=ft.KeyboardType.NUMBER)
        progress = ft.ProgressBar(value=0, visible=False)
        status = ft.Text("")
        run_btn = ft.FilledButton("Comprimir", icon=ft.Icons.PLAY_ARROW, disabled=True)
        open_btn = ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                     visible=False)

        def on_pick(e: ft.FilePickerResultEvent) -> None:
            # En el navegador (modo web) f.path es None; estas herramientas
            # necesitan rutas locales, así que solo operan en escritorio.
            if e.files and e.files[0].path:
                selected["file"] = Path(e.files[0].path)
                file_label.value = selected["file"].name
                file_label.italic = False
                run_btn.disabled = False
                page.update()
            elif e.files:
                status.value = "El modo navegador no da rutas locales; usa la app de escritorio."
                page.update()

        picker = self._picker
        # Rebind on_result to the current closure (new build call may have new locals).
        picker.on_result = on_pick
        if picker not in page.overlay:
            page.overlay.append(picker)

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

        def do_run(e) -> None:
            if not selected["file"]:
                return
            try:
                params = CompressParams(target_mb=float(target_field.value))
            except (ValueError, ValidationError):
                status.value = "Tamaño objetivo inválido"
                page.update()
                return
            run_btn.disabled = True
            open_btn.visible = False
            progress.visible = True
            progress.value = 0
            page.update()
            ctx.run_job(
                work=lambda prog: compress([selected["file"]], params, progress=prog),
                on_progress=set_progress,
                on_done=on_done,
                on_error=on_error,
            )

        def open_folder(e) -> None:
            _open_folder(Path(open_btn.data))

        run_btn.on_click = do_run
        open_btn.on_click = open_folder

        return ft.Column(
            [
                ft.Text(self.meta.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(self.meta.description),
                ft.Divider(),
                ft.Row([
                    ft.FilledTonalButton(
                        "Elegir PDF", icon=ft.Icons.UPLOAD_FILE,
                        on_click=lambda _: picker.pick_files(
                            allow_multiple=False, allowed_extensions=["pdf"])),
                    file_label,
                ]),
                target_field,
                ft.Row([run_btn, open_btn]),
                progress,
                status,
            ],
            spacing=16,
        )
