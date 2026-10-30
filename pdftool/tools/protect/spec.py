from pdftool.core.plugin import ToolMeta, ToolSpec
from pdftool.core.registry import register
from pdftool.tools.protect.logic import protect
from pdftool.tools.protect.params import ProtectParams

SPEC = register(
    ToolSpec(
        meta=ToolMeta(
            id="protect",
            name="Proteger PDF",
            description="Añade o quita la contraseña de uno o varios PDFs.",
            category="Seguridad",
            order=60,
        ),
        params=ProtectParams,
        run=protect,
    )
)
