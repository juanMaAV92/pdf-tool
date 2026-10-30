from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.merge.logic import merge
from pdftool.tools.merge.params import MergeParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="merge",
            name="Unir PDFs",
            description="Combina varios PDFs en uno solo, en el orden que elijas.",
            category="Organizar",
            order=10,
        ),
        params=MergeParams,
        run=merge,
        min_inputs=2,
    )
)
