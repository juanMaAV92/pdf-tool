from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.split.logic import split
from pdftool.tools.split.params import SplitParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="split",
            name="Dividir PDF",
            description="Separa un PDF en varios, por rangos o por páginas.",
            category="Organizar",
            order=20,
        ),
        params=SplitParams,
        run=split,
    )
)
