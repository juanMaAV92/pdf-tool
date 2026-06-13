from pathlib import Path
from pdftool.core.plugin import ToolMeta, ToolResult


def test_toolmeta_holds_metadata():
    m = ToolMeta(id="x", name="X", description="d", icon="i", category="c")
    assert m.id == "x" and m.category == "c"


def test_toolresult_holds_outputs_and_summary():
    r = ToolResult(outputs=[Path("a.pdf")], summary="ok")
    assert r.outputs == [Path("a.pdf")] and r.summary == "ok"
