from __future__ import annotations

from pathlib import Path

import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.core.registry import register
from pdftool.tools.images2pdf.logic import images_to_pdf
from pdftool.tools.images2pdf.params import ImagesToPdfParams
from pdftool.ui.panel_base import MultiFileToolPanel


@register
class ImagesToPdfTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="images2pdf",
        name="Imágenes a PDF",
        description="Convierte cada imagen (JPG/PNG) en su propio PDF.",
        icon=ft.Icons.PICTURE_AS_PDF,
        category="Convertir",
    )
    run_label = "Convertir"
    run_icon = ft.Icons.PICTURE_AS_PDF
    pick_label = "Añadir imágenes"
    pick_icon = ft.Icons.ADD_PHOTO_ALTERNATE
    allowed_extensions = ["jpg", "jpeg", "png"]
    min_files = 1

    def make_params(self):
        return ImagesToPdfParams()

    def run_logic(self, inputs: list[Path], params, progress):
        return images_to_pdf(inputs, params, progress=progress)
