import json
from pathlib import Path

from pdftool.cli.report import error_to_dict, exit_code, render_text, result_to_dict
from pdftool.core.errors import GENERIC_MESSAGE, UserError
from pdftool.core.plugin import FileResult, ToolResult


def _batch(*, fail: bool = False) -> ToolResult:
    items = [
        FileResult(
            Path("/in/a.pdf"),
            Path("/out/a_comp.pdf"),
            True,
            "2 MB → 1 MB",
            warnings=("se rasterizaron páginas",),
            metrics={"saved_pct": 50.0},
        )
    ]
    if fail:
        items.append(FileResult(Path("/in/b.pdf"), None, False, "No se pudo"))
    return ToolResult(
        outputs=[Path("/out/a_comp.pdf")], summary="1 de 2 listos", items=items
    )


def test_result_to_dict_with_items():
    data = result_to_dict("compress", _batch())
    assert data["ok"] is True
    assert data["tool"] == "compress"
    assert data["outputs"] == ["/out/a_comp.pdf"]
    assert data["items"][0] == {
        "input": "/in/a.pdf",
        "output": "/out/a_comp.pdf",
        "ok": True,
        "message": "2 MB → 1 MB",
        "warnings": ["se rasterizaron páginas"],
        "metrics": {"saved_pct": 50.0},
    }


def test_partial_batch_is_not_ok_and_exits_3():
    result = _batch(fail=True)
    assert result_to_dict("compress", result)["ok"] is False
    assert result_to_dict("compress", result)["items"][1]["output"] is None
    assert exit_code(result) == 3
    assert exit_code(_batch()) == 0


def test_error_to_dict_hides_detail_for_user_errors():
    data = error_to_dict("split", UserError("Rango inválido"))
    assert data == {
        "ok": False,
        "tool": "split",
        "error": {"message": "Rango inválido", "detail": None},
    }


def test_error_to_dict_keeps_detail_for_unexpected():
    data = error_to_dict("watermark", RuntimeError("boom"))
    assert data["error"]["message"] == GENERIC_MESSAGE
    assert "RuntimeError" in data["error"]["detail"]


def test_render_text_marks_failed_items():
    text = render_text(_batch(fail=True))
    assert text.splitlines()[0] == "1 de 2 listos"
    assert "✓ a.pdf: 2 MB → 1 MB" in text
    assert "  aviso: se rasterizaron páginas" in text
    assert "✗ b.pdf: No se pudo" in text


def test_render_text_lists_outputs_without_items():
    result = ToolResult(outputs=[Path("/out/x.pdf")], summary="Listo")
    assert render_text(result) == "Listo\n/out/x.pdf"


def test_json_is_serializable():
    json.dumps(result_to_dict("compress", _batch(fail=True)))
