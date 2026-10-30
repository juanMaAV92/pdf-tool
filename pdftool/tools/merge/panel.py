from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.naming import parse_output_name
from pdftool.tools.merge.logic import output_path_for_merge
from pdftool.tools.merge.params import MergeParams
from pdftool.tools.merge.spec import SPEC
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import OutputNameField
from pdftool.ui.registry import register


@register
class MergeTool(MultiFileToolPanel):
    spec = SPEC
    icon = ft.Icons.MERGE
    run_label = "Unir"
    run_icon = ft.Icons.MERGE_TYPE
    pick_label = "Añadir PDFs"
    pick_icon = ft.Icons.UPLOAD_FILE
    show_thumbnails = True
    reorderable = True

    def extra_controls(self) -> list[ft.Control]:
        self._name_field = OutputNameField(resolve=self._resolve_output)
        return [self._name_field]

    def _resolve_output(self, base: str | None) -> Path | None:
        """Ruta real que usaría el run, o None si aún no hay archivos."""
        if not self._files:
            return None
        return output_path_for_merge(self._files, base, self._out_dir.value)

    def on_inputs_changed(self) -> None:
        self._name_field.refresh()

    def on_output_dir_changed(self) -> None:
        self._name_field.refresh()

    def make_params(self):
        return MergeParams(output_name=parse_output_name(self._name_field.value))
