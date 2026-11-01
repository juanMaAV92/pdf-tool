from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.compress.logic import compress
from pdftool.tools.compress.params import CompressParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="compress",
            category="optimize",
            order=30,
        ),
        params=CompressParams,
        run=compress,
    )
)
