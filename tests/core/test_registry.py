from pdftool.core import registry
from pdftool.core.plugin import PdfTool, ToolMeta, ToolContext


def test_register_and_get_tools():
    registry.clear()

    @registry.register
    class Dummy(PdfTool):
        meta = ToolMeta(id="dummy", name="D", description="d", icon="i", category="c")

        def build_panel(self, ctx: ToolContext):
            return None

    tools = registry.get_tools()
    assert len(tools) == 1
    assert tools[0].meta.id == "dummy"


def test_register_is_idempotent_by_id():
    registry.clear()

    @registry.register
    class A(PdfTool):
        meta = ToolMeta(id="same", name="A", description="d", icon="i", category="c")
        def build_panel(self, ctx): return None

    @registry.register
    class B(PdfTool):
        meta = ToolMeta(id="same", name="B", description="d", icon="i", category="c")
        def build_panel(self, ctx): return None

    assert len(registry.get_tools()) == 1
