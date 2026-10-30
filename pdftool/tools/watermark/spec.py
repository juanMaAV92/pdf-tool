from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.watermark.logic import watermark
from pdftool.tools.watermark.params import WatermarkParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="watermark",
            name="Marca de agua",
            description="Repite un texto en diagonal sobre todas las páginas.",
            category="Editar",
            order=50,
        ),
        params=WatermarkParams,
        run=watermark,
        max_inputs=1,
    )
)
