from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.images2pdf.logic import images_to_pdf
from pdftool.tools.images2pdf.params import ImagesToPdfParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="images2pdf",
            name="Imágenes a PDF",
            description="Crea un PDF por cada imagen (JPG o PNG).",
            category="Convertir",
            order=40,
        ),
        params=ImagesToPdfParams,
        run=images_to_pdf,
    )
)
