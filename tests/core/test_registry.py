import pytest

from pdftool.core import registry
from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta


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


def _tool(id_, name="T", order=100):
    class T(PdfTool):
        meta = ToolMeta(
            id=id_, name=name, description="d", icon="i", category="c", order=order
        )

        def build_panel(self, ctx):
            return None

    return T


def test_registering_the_same_class_twice_is_harmless():
    registry.clear()
    cls = _tool("same")
    registry.register(cls)
    registry.register(cls)
    assert len(registry.get_tools()) == 1


def test_duplicate_id_from_another_class_is_rejected():
    registry.clear()
    registry.register(_tool("same", "A"))
    with pytest.raises(ValueError, match="same"):
        registry.register(_tool("same", "B"))


def test_tools_follow_the_declared_order():
    registry.clear()
    registry.register(_tool("c", "Zeta", order=10))
    registry.register(_tool("a", "Alfa", order=30))
    registry.register(_tool("b", "Beta", order=20))
    assert [t.meta.id for t in registry.get_tools()] == ["c", "b", "a"]


def test_a_tool_that_fails_to_import_does_not_break_discovery(tmp_path, monkeypatch):
    pkg = tmp_path / "fake_tools"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "good.py").write_text(
        "from pdftool.core import registry\n"
        "from pdftool.core.plugin import PdfTool, ToolMeta\n"
        "@registry.register\n"
        "class Good(PdfTool):\n"
        "    meta = ToolMeta(id='good', name='G', description='d', icon='i',"
        " category='c')\n"
        "    def build_panel(self, ctx):\n"
        "        return None\n"
    )
    (pkg / "broken.py").write_text("raise ImportError('falta una dependencia')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    registry.clear()

    failed = registry.discover("fake_tools")

    assert failed == ["broken"]
    assert [t.meta.id for t in registry.get_tools()] == ["good"]


def test_real_tools_are_ordered_by_task():
    registry.discover()
    ids = [t.meta.id for t in registry.get_tools()]
    expected = ["merge", "split", "compress", "images2pdf", "watermark", "protect"]
    assert [i for i in ids if i in expected] == expected
