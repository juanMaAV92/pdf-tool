from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.compress.logic import compress
from pdftool.tools.compress.params import CompressParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="compress",
            name="Comprimir PDF",
            description="Reduce el tamaño de uno o varios PDFs a un objetivo en MB.",
            category="Optimizar",
            order=30,
        ),
        params=CompressParams,
        run=compress,
    )
)
