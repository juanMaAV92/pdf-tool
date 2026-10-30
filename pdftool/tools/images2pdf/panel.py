from __future__ import annotations

import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.tools.images2pdf.logic import images_to_pdf
from pdftool.tools.images2pdf.params import ImagesToPdfParams
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.registry import register


@register
class ImagesToPdfTool(MultiFileToolPanel):
    meta = ToolMeta(
        id="images2pdf",
        name="Imágenes a PDF",
        description="Crea un PDF por cada imagen (JPG o PNG).",
        category="Convertir",
        order=40,
    )
    icon = ft.Icons.PHOTO_LIBRARY
    logic = staticmethod(images_to_pdf)
    run_label = "Convertir"
    run_icon = ft.Icons.PICTURE_AS_PDF
    pick_label = "Añadir imágenes"
    pick_icon = ft.Icons.ADD_PHOTO_ALTERNATE
    allowed_extensions = ("jpg", "jpeg", "png")
    min_files = 1
    show_thumbnails = True

    def make_params(self):
        return ImagesToPdfParams()
