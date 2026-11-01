import pytest

from pdftool.core.plugin import PdfTool, ToolContext, ToolMeta
from pdftool.ui import registry


def test_register_and_get_tools():
    registry.clear()

    @registry.register
    class Dummy(PdfTool):
        meta = ToolMeta(id="dummy", category="c")

        def build_panel(self, ctx: ToolContext):
            return None

    tools = registry.get_tools()
    assert len(tools) == 1
    assert tools[0].meta.id == "dummy"


def _tool(id_, name="T", order=100):
    class T(PdfTool):
        meta = ToolMeta(id=id_, category="c", order=order)

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
    (pkg / "good").mkdir()
    (pkg / "good" / "__init__.py").write_text("")
    (pkg / "good" / "panel.py").write_text(
        "from pdftool.ui import registry\n"
        "from pdftool.core.plugin import PdfTool, ToolMeta\n"
        "@registry.register\n"
        "class Good(PdfTool):\n"
        "    meta = ToolMeta(id='good', "
        "category='c')\n"
        "    def build_panel(self, ctx):\n"
        "        return None\n"
    )
    (pkg / "broken").mkdir()
    (pkg / "broken" / "__init__.py").write_text("")
    (pkg / "broken" / "panel.py").write_text(
        "raise ImportError('falta una dependencia')\n"
    )
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


def test_every_spec_has_a_panel_and_vice_versa():
    # App y CLI crecen a la par: ninguna herramienta existe solo en una.
    from pdftool.core import registry as specs

    specs.clear()
    registry.clear()
    specs.discover()
    registry.discover()
    by_id = {s.meta.id: s for s in specs.get_specs()}
    panels = {t.meta.id: type(t) for t in registry.get_tools()}
    assert set(by_id) == set(panels)
    for tool_id, cls in panels.items():
        assert cls.spec is by_id[tool_id]


def test_panels_take_input_rules_from_their_spec():
    from pdftool.core import registry as specs
    from pdftool.ui.file_list import MultiFileToolPanel
    from pdftool.ui.panel_base import SingleFileToolPanel

    specs.discover()
    registry.discover()
    for tool in registry.get_tools():
        cls, spec = type(tool), type(tool).spec
        assert cls.allowed_extensions == spec.extensions
        if issubclass(cls, MultiFileToolPanel):
            assert cls.min_files == spec.min_inputs
        if issubclass(cls, SingleFileToolPanel):
            assert spec.max_inputs == 1
