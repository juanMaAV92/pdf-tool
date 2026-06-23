from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import flet as ft

from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta
from pdftool.core.registry import register
from pdftool.tools.images2pdf.logic import images_to_pdf
from pdftool.tools.images2pdf.params import ImagesToPdfParams


def _open_folder(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


@register
class ImagesToPdfTool(PdfTool):
    meta = ToolMeta(
        id="images2pdf",
        name="Imágenes a PDF",
        description="Combina varias imágenes (JPG/PNG) en un solo PDF, en el orden que elijas.",
        icon=ft.Icons.PICTURE_AS_PDF,
        category="Convertir",
    )

    def __init__(self) -> None:
        self._picker = ft.FilePicker()

    def build_panel(self, ctx: ToolContext) -> ft.Control:
        page: ft.Page = ctx.page
        files: list[Path] = []

        file_list = ft.Column(spacing=4)
        progress = ft.ProgressBar(value=0, visible=False)
        status = ft.Text("")
        run_btn = ft.FilledButton("Crear PDF", icon=ft.Icons.PICTURE_AS_PDF,
                                  disabled=True)
        open_btn = ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                     visible=False)

        def refresh() -> None:
            file_list.controls.clear()
            for index, path in enumerate(files):
                file_list.controls.append(
                    ft.Row(
                        [
                            ft.Text(f"{index + 1}.", width=28),
                            ft.Text(path.name, expand=True,
                                    overflow=ft.TextOverflow.ELLIPSIS),
                            ft.IconButton(ft.Icons.ARROW_UPWARD, tooltip="Subir",
                                          disabled=index == 0,
                                          on_click=lambda _e, i=index: move(i, -1)),
                            ft.IconButton(ft.Icons.ARROW_DOWNWARD, tooltip="Bajar",
                                          disabled=index == len(files) - 1,
                                          on_click=lambda _e, i=index: move(i, 1)),
                            ft.IconButton(ft.Icons.CLOSE, tooltip="Quitar",
                                          on_click=lambda _e, i=index: remove(i)),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    )
                )
            run_btn.disabled = len(files) < 1
            page.update()

        def move(index: int, delta: int) -> None:
            new_index = index + delta
            if 0 <= new_index < len(files):
                files[index], files[new_index] = files[new_index], files[index]
                refresh()

        def remove(index: int) -> None:
            files.pop(index)
            refresh()

        def on_pick(e: ft.FilePickerResultEvent) -> None:
            if not e.files:
                return
            added = 0
            for f in e.files:
                if not f.path:  # navegador (modo web): sin ruta local
                    continue
                p = Path(f.path)
                if p not in files:
                    files.append(p)
                    added += 1
            if added == 0 and e.files:
                status.value = "El modo navegador no da rutas locales; usa la app de escritorio."
            else:
                open_btn.visible = False
                status.value = ""
            refresh()

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
            run_btn.disabled = len(files) < 1
            page.update()

        def on_error(exc: Exception) -> None:
            progress.visible = False
            status.value = f"Error: {exc}"
            run_btn.disabled = len(files) < 1
            page.update()

        def do_run(_e) -> None:
            if not files:
                return
            run_btn.disabled = True
            open_btn.visible = False
            progress.visible = True
            progress.value = 0
            page.update()
            current = list(files)
            ctx.run_job(
                work=lambda prog: images_to_pdf(current, ImagesToPdfParams(),
                                                progress=prog),
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
                ft.FilledTonalButton(
                    "Añadir imágenes", icon=ft.Icons.ADD_PHOTO_ALTERNATE,
                    on_click=lambda _e: self._picker.pick_files(
                        allow_multiple=True, allowed_extensions=["jpg", "jpeg", "png"])),
                file_list,
                ft.Row([run_btn, open_btn]),
                progress,
                status,
            ],
            spacing=16,
        )
