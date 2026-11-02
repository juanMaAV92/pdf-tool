from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.pdf2images.logic import pdf2images
from pdftool.tools.pdf2images.params import Pdf2ImagesParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="pdf2images",
            category="convert",
            order=45,
        ),
        params=Pdf2ImagesParams,
        run=pdf2images,
    )
)
