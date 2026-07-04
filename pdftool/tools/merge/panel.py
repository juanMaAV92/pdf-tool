from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.merge.logic import merge
from pdftool.tools.merge.params import MergeParams
from pdftool.ui.panel_base import MultiFileToolPanel


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

    def make_params(self):
        return MergeParams()

    def run_logic(self, inputs: list[Path], params, progress):
        return merge(inputs, params, progress=progress)
