from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.logger import log_paths

_EMPTY = "(registro vacío)\n"


def _log_content() -> str:
    chunks: list[str] = []
    for p in log_paths():
        try:
            chunks.append(p.read_text(encoding="utf-8"))
        except OSError:  # rotación entre exists() y read_text(): archivo ilegible
            continue
    return "".join(chunks) if chunks else _EMPTY


def make_log_picker() -> ft.FilePicker:
    """FilePicker de "guardar como" que escribe el log en la ruta elegida.

    El llamador debe añadirlo a page.overlay (una sola vez).
    """
    def on_save(e: ft.FilePickerResultEvent) -> None:
        if not e.path:  # diálogo cancelado (o modo web sin ruta)
            return
        target = Path(e.path)
        if target.suffix.lower() != ".txt":
            target = target.with_suffix(".txt")
        target.write_text(_log_content(), encoding="utf-8")

    return ft.FilePicker(on_result=on_save)


def download_log_button(picker: ft.FilePicker) -> ft.Control:
    """Botón "Descargar log": abre el diálogo de guardado sobre `picker`."""
    return ft.TextButton(
        "Descargar log", icon=ft.Icons.DOWNLOAD,
        on_click=lambda _e: picker.save_file(
            dialog_title="Guardar log", file_name="pdf-tool-log.txt",
            allowed_extensions=["txt"]),
    )
