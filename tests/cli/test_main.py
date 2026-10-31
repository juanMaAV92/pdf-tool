import io
import json
from pathlib import Path

import pymupdf

from pdftool import __version__
from pdftool.cli import main
from pdftool.core.errors import GENERIC_MESSAGE
from tests.conftest import _make_pdf


def _json(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_version(capsys):
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_list_json_has_all_tools_and_input_rules(capsys):
    assert main(["list", "--json"]) == 0
    tools = {t["id"]: t for t in json.loads(capsys.readouterr().out)}
    assert set(tools) == {
        "merge",
        "split",
        "compress",
        "images2pdf",
        "watermark",
        "protect",
    }
    assert tools["merge"]["inputs"] == {"min": 2, "max": None, "extensions": ["pdf"]}
    assert "target_mb" in tools["compress"]["params"]["properties"]


def test_list_text_shows_one_line_per_tool(capsys):
    assert main(["list"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 6
    assert lines[0].startswith("merge")


def test_compress_json_end_to_end(small_pdf, tmp_path, capsys):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    before = small_pdf.read_bytes()
    code = main(["compress", str(small_pdf), "--output-dir", str(out_dir), "--json"])
    data = _json(capsys)
    assert code == 0
    assert data["ok"] is True and data["tool"] == "compress"
    assert Path(data["outputs"][0]).parent == out_dir
    assert Path(data["outputs"][0]).exists()
    assert small_pdf.read_bytes() == before


def test_merge_needs_two_inputs(small_pdf, capsys):
    assert main(["merge", str(small_pdf)]) == 2
    assert "al menos 2" in capsys.readouterr().err


def test_split_accepts_one_input(tmp_path, capsys):
    a = _make_pdf(tmp_path / "a.pdf", pages=2)
    b = _make_pdf(tmp_path / "b.pdf")
    assert main(["split", str(a), str(b)]) == 2
    assert main(["split", str(a), "--mode", "single"]) == 0
    assert len(list(tmp_path.glob("a_*.pdf"))) == 2


def test_missing_file_is_a_usage_error(tmp_path, capsys):
    missing = tmp_path / "nope.pdf"
    assert main(["compress", str(missing), "--json"]) == 2
    data = _json(capsys)
    assert data["ok"] is False and "nope.pdf" in data["error"]["message"]
    assert list(tmp_path.iterdir()) == []


def test_wrong_extension_is_a_usage_error(tmp_path):
    txt = tmp_path / "a.txt"
    txt.write_text("hola")
    assert main(["compress", str(txt)]) == 2


def test_protect_reads_password_from_stdin(small_pdf, capsys):
    code = main(
        ["protect", str(small_pdf), "--password-stdin", "--json"],
        stdin=io.StringIO("pw\n"),
    )
    data = _json(capsys)
    assert code == 0
    with pymupdf.open(data["outputs"][0]) as doc:
        assert doc.needs_pass


def test_protect_without_password_is_a_usage_error(small_pdf, capsys):
    assert main(["protect", str(small_pdf)], env={}) == 2
    assert "--password-stdin" in capsys.readouterr().err


def test_runtime_failure_exits_1_with_json_error(tmp_path, capsys):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"esto no es un pdf")
    assert main(["watermark", str(broken), "--text", "x", "--json"]) == 1
    data = _json(capsys)
    assert data["error"]["message"] == GENERIC_MESSAGE
    assert data["error"]["detail"]


def test_human_output_goes_to_stdout_errors_to_stderr(small_pdf, tmp_path, capsys):
    assert main(["watermark", str(small_pdf), "--text", "BORRADOR"]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() and not captured.err
    assert main(["compress", str(tmp_path / "nope.pdf")]) == 2
    captured = capsys.readouterr()
    assert not captured.out and captured.err.startswith("pdf-tool: ")


def test_usage_errors_are_json_with_json_flag(small_pdf, capsys):
    for argv in (
        ["split", str(small_pdf), "--mode", "nope", "--json"],
        ["compress", "--json"],
        ["compress", str(small_pdf), "--bogus", "--json"],
    ):
        assert main(argv) == 2
        data = _json(capsys)
        assert data["ok"] is False and data["error"]["message"]


def test_missing_output_dir_is_a_usage_error(small_pdf, tmp_path, capsys):
    missing = tmp_path / "no" / "existe"
    code = main(
        ["watermark", str(small_pdf), "--text", "x", "--output-dir", str(missing)]
    )
    assert code == 2
    assert "carpeta de salida" in capsys.readouterr().err


def test_cli_parser_builds_for_all_real_specs():
    from pdftool.cli import _build_parser
    from pdftool.core import registry

    registry.discover()
    _build_parser(registry.get_specs())
