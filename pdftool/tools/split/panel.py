from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import fitz
import flet as ft

from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta
from pdftool.core.registry import register
from pdftool.tools.split.logic import parse_ranges, resolve_ranges, split
from pdftool.tools.split.params import SplitParams

_RANGES_HELP = (
    "Cómo escribir rangos:\n"
    "  1-3    →  páginas 1 a la 3\n"
    "  5      →  solo la página 5\n"
    "  8-     →  de la página 8 hasta el final\n"
    "  -4     →  del inicio hasta la página 4\n"
    "Separa varios rangos con comas:\n"
    "  1-3, 5, 8-"
)


def _open_folder(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


@register
class SplitTool(PdfTool):
    meta = ToolMeta(
        id="split",
        name="Dividir PDF",
        description="Separa un PDF en varios, por rangos o por páginas.",
        icon=ft.Icons.CONTENT_CUT,
        category="Organizar",
    )

    def __init__(self) -> None:
        self._picker = ft.FilePicker()

    def build_panel(self, ctx: ToolContext) -> ft.Control:
        page: ft.Page = ctx.page
        selected: dict[str, object] = {"file": None, "pages": 0}

        file_label = ft.Text("Ningún archivo seleccionado", italic=True)
        ranges_field = ft.TextField(
            label="Rangos", hint_text="ej: 1-3, 5, 8-", width=240, disabled=False)
        every_field = ft.TextField(
            label="Cada N páginas", value="10", width=160, disabled=True,
            keyboard_type=ft.KeyboardType.NUMBER)
        mode = ft.RadioGroup(
            value="ranges",
            content=ft.Column([
                ft.Row([
                    ft.Radio(value="ranges", label="Por rangos"),
                    ranges_field,
                    ft.IconButton(ft.Icons.HELP_OUTLINE, tooltip=_RANGES_HELP),
                ]),
                ft.Radio(value="single", label="Una página por archivo"),
                ft.Row([
                    ft.Radio(value="every", label="Cada"),
                    every_field,
                    ft.Text("páginas"),
                ]),
            ], spacing=8),
        )

        progress = ft.ProgressBar(value=0, visible=False)
        status = ft.Text("")
        run_btn = ft.FilledButton("Dividir", icon=ft.Icons.CONTENT_CUT, disabled=True)
        open_btn = ft.OutlinedButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                     visible=False)

        def on_mode_change(_e) -> None:
            ranges_field.disabled = mode.value != "ranges"
            every_field.disabled = mode.value != "every"
            page.update()

        mode.on_change = on_mode_change

        def on_pick(e: ft.FilePickerResultEvent) -> None:
            if e.files and e.files[0].path:
                path = Path(e.files[0].path)
                with fitz.open(str(path)) as doc:
                    pages = doc.page_count
                selected["file"] = path
                selected["pages"] = pages
                file_label.value = f"{path.name} · {pages} páginas"
                file_label.italic = False
                run_btn.disabled = False
                open_btn.visible = False
                status.value = ""
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
            src = selected["file"]
            if not src:
                return
            try:
                params = SplitParams(
                    mode=mode.value,
                    ranges=ranges_field.value or "",
                    every_n=int(every_field.value) if every_field.value else 1,
                )
                if params.mode == "ranges":
                    # Valida la sintaxis y los límites antes de lanzar el job.
                    resolve_ranges(parse_ranges(params.ranges), int(selected["pages"]))
            except ValueError as exc:
                status.value = str(exc)
                page.update()
                return
            except Exception:  # noqa: BLE001  (pydantic/int inválido)
                status.value = "Parámetros inválidos"
                page.update()
                return

            run_btn.disabled = True
            open_btn.visible = False
            progress.visible = True
            progress.value = 0
            page.update()
            ctx.run_job(
                work=lambda prog: split([src], params, progress=prog),
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
                        on_click=lambda _: self._picker.pick_files(
                            allow_multiple=False, allowed_extensions=["pdf"])),
                    file_label,
                ]),
                ft.Text("Cómo dividir:", weight=ft.FontWeight.W_500),
                mode,
                ft.Row([run_btn, open_btn]),
                progress,
                status,
            ],
            spacing=16,
        )
