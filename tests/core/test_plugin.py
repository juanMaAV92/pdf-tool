from pathlib import Path
from pdftool.core.plugin import ToolMeta, ToolResult


def test_toolmeta_holds_metadata():
    m = ToolMeta(id="x", name="X", description="d", icon="i", category="c")
    assert m.id == "x" and m.category == "c"


def test_toolresult_holds_outputs_and_summary():
    r = ToolResult(outputs=[Path("a.pdf")], summary="ok")
    assert r.outputs == [Path("a.pdf")] and r.summary == "ok"


from pathlib import Path

from pdftool.core.plugin import BaseParams
from pdftool.tools.compress.params import CompressParams
from pdftool.tools.images2pdf.params import ImagesToPdfParams
from pdftool.tools.merge.params import MergeParams
from pdftool.tools.protect.params import ProtectParams
from pdftool.tools.split.params import SplitParams
from pdftool.tools.watermark.params import WatermarkParams


def test_base_params_defaults_to_no_output_dir():
    assert BaseParams().output_dir is None


def test_every_tool_params_inherits_output_dir():
    """Las seis herramientas aceptan un destino; None es «junto al original»."""
    made = [
        MergeParams(),
        CompressParams(),
        ProtectParams(password="x"),
        SplitParams(),
        WatermarkParams(text="x"),
        ImagesToPdfParams(),
    ]
    for params in made:
        assert isinstance(params, BaseParams)
        assert params.output_dir is None


def test_output_dir_accepts_a_path():
    assert MergeParams(output_dir=Path("/tmp/x")).output_dir == Path("/tmp/x")


def test_existing_fields_still_work():
    assert MergeParams(output_name="informe").output_name == "informe"
    assert CompressParams(target_mb=2.5).target_mb == 2.5
