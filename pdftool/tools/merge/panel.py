from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.merge.logic import merge, output_path_for_merge
from pdftool.tools.merge.params import MergeParams
from pdftool.ui.panel_base import (MultiFileToolPanel, OutputNameField,
                                   parse_output_name)


@register
class MergeTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="merge",
        name="Unir PDFs",
        description="Combina varios PDFs en uno solo, en el orden que elijas.",
        icon=ft.Icons.MERGE,
        category="Organizar",
    )
    run_label = "Unir"
    run_icon = ft.Icons.MERGE_TYPE
    pick_label = "Añadir PDFs"
    pick_icon = ft.Icons.UPLOAD_FILE
    allowed_extensions = ["pdf"]
    min_files = 2
    show_thumbnails = True

    def extra_controls(self) -> list[ft.Control]:
        self._name_field = OutputNameField(resolve=self._resolve_output)
        return [self._name_field]

    def _resolve_output(self, base: str | None) -> Path | None:
        """Ruta real que usaría el run, o None si aún no hay archivos."""
        if not self._files:
            return None
        return output_path_for_merge(self._files, base)

    def on_inputs_changed(self) -> None:
        self._name_field.refresh()

    def make_params(self):
        return MergeParams(output_name=parse_output_name(self._name_field.value))

    def run_logic(self, inputs: list[Path], params, progress):
        return merge(inputs, params, progress=progress)
