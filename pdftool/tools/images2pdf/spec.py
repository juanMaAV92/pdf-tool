from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.images2pdf.logic import images_to_pdf
from pdftool.tools.images2pdf.params import ImagesToPdfParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="images2pdf",
            category="convert",
            order=40,
        ),
        params=ImagesToPdfParams,
        run=images_to_pdf,
        extensions=("jpg", "jpeg", "png"),
    )
)
