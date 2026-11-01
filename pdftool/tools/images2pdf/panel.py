from __future__ import annotations

import flet as ft

from pdftool.tools.images2pdf.params import ImagesToPdfParams
from pdftool.tools.images2pdf.spec import SPEC
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.registry import register


@register
class ImagesToPdfTool(MultiFileToolPanel):
    spec = SPEC
    icon = ft.Icons.PHOTO_LIBRARY
    run_label_key = "tool.images2pdf.ui.run"
    run_icon = ft.Icons.PICTURE_AS_PDF
    pick_label_key = "tool.images2pdf.ui.pick"
    pick_icon = ft.Icons.ADD_PHOTO_ALTERNATE
    show_thumbnails = True

    def make_params(self):
        return ImagesToPdfParams()
