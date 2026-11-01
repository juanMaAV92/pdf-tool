from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import flet as ft

from pdftool.core.logger import log_paths
from pdftool.i18n import t


def _log_content() -> str:
    chunks: list[str] = []
    for p in log_paths():
        try:
            chunks.append(p.read_text(encoding="utf-8"))
        except OSError:  # rotación entre exists() y read_text(): archivo ilegible
            continue
    return "".join(chunks) if chunks else t("ui.log.empty") + "\n"


def log_label() -> str:
    return t("ui.log.label")


def make_log_picker(
    on_saved: Callable[[Path], None] | None = None,
) -> ft.FilePicker:
    """FilePicker de "guardar como" que escribe el log en la ruta elegida.

    El llamador debe añadirlo a page.overlay (una sola vez). `on_saved` recibe
    la ruta final para confirmar al usuario dónde quedó el informe.
    """

    def on_save(e: ft.FilePickerResultEvent) -> None:
        if not e.path:  # diálogo cancelado (o modo web sin ruta)
            return
        target = Path(e.path)
        if target.suffix.lower() != ".txt":
            target = target.with_suffix(".txt")
        target.write_text(_log_content(), encoding="utf-8")
        if on_saved is not None:
            on_saved(target)

    return ft.FilePicker(on_result=on_save)


def download_log_button(picker: ft.FilePicker) -> ft.Control:
    """Botón del informe de diagnóstico: abre el diálogo de guardado."""
    return ft.TextButton(
        log_label(),
        icon=ft.Icons.DOWNLOAD,
        on_click=lambda _e: picker.save_file(
            dialog_title=log_label(),
            file_name="pdf-tool-log.txt",
            allowed_extensions=["txt"],
        ),
    )
