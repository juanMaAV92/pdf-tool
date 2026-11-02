from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.organize.logic import organize
from pdftool.tools.organize.params import OrganizeParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="organize",
            category="organize",
            order=25,
        ),
        params=OrganizeParams,
        run=organize,
        max_inputs=1,
    )
)
