"""Idioma de la CLI: --lang, PDFTOOL_LANG y textos traducidos."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from pdftool import i18n
from pdftool.cli import main
from pdftool.cli.report import render_text
from pdftool.core.plugin import FileResult, ToolResult


def _run(argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv, env=env or {})
    return code, out.getvalue(), err.getvalue()


@pytest.mark.parametrize(
    "argv",
    [["--lang", "en", "list"], ["list", "--lang", "en"], ["list", "--lang=en"]],
)
def test_lang_flag_any_position(argv):
    code, out, _ = _run(argv)
    assert code == 0
    assert "Merge PDFs" in out


def test_env_var_and_precedence():
    _, out, _ = _run(["list"], env={"PDFTOOL_LANG": "en"})
    assert "Merge PDFs" in out
    _, out, _ = _run(["list", "--lang", "es"], env={"PDFTOOL_LANG": "en"})
    assert "Unir PDFs" in out


def test_no_flag_uses_system_language(monkeypatch):
    monkeypatch.setattr(i18n, "_ui_language", lambda: "en-US")
    _, out, _ = _run(["list"])
    assert "Merge PDFs" in out


def test_invalid_lang_is_usage_error_listing_languages():
    code, _, err = _run(["--lang", "de", "list"])
    assert code == 2
    assert "en" in err and "es" in err


def test_invalid_lang_with_json_reports_json():
    code, out, _ = _run(["--lang", "de", "list", "--json"])
    assert code == 2
    data = json.loads(out)
    assert data["ok"] is False
    assert "es" in data["error"]["message"]


def test_errors_follow_language(tmp_path):
    missing = tmp_path / "nope.pdf"
    code, out, _ = _run(["--lang", "en", "compress", str(missing), "--json"])
    assert code == 2
    message = json.loads(out)["error"]["message"]
    assert message == i18n.t("cli.error.not_found", path=missing)
    assert "No existe" not in message


def test_generic_message_follows_language():
    from pdftool.core.errors import user_message

    i18n.set_language("en")
    message, detail = user_message(RuntimeError("boom"))
    assert message == i18n.t("core.error.generic")
    assert detail == "RuntimeError: boom"


def test_pydantic_errors_are_translated(small_pdf):
    code, out, _ = _run(["compress", str(small_pdf), "--target-mb", "-1", "--json"])
    assert code == 2
    message = json.loads(out)["error"]["message"]
    assert message.startswith("--target-mb: ")
    assert "Input should" not in message
    assert message == "--target-mb: " + i18n.t("cli.validation.greater_than", gt=0)


def test_report_text_prefixes_follow_language(tmp_path):
    item = FileResult(tmp_path / "a.pdf", None, False, "x", warnings=("w",))
    result = ToolResult(outputs=[], summary="s", items=[item], warnings=["g"])
    i18n.set_language("en")
    text = render_text(result)
    assert "  warning: w" in text and "\nwarning: g" in text


def test_gui_missing_message_follows_language():
    from pdftool.main import gui_missing

    i18n.set_language("en")
    assert "pipx install 'pdf-tool-cli[gui]'" in gui_missing()
    assert gui_missing() == i18n.t("app.gui_missing")


def test_lang_flag_wins_over_an_invalid_env_var():
    code, out, _ = _run(["--lang", "en", "list"], env={"PDFTOOL_LANG": "pt"})
    assert code == 0
    assert "Merge PDFs" in out


def test_list_json_keeps_params_description():
    _, out, _ = _run(["--lang", "en", "list", "--json"])
    merge = next(t for t in json.loads(out) if t["id"] == "merge")
    assert merge["params"]["description"] == i18n.t("tool.merge.description")


def test_abbreviated_lang_is_rejected_not_ignored():
    code, _, _err = _run(["--lan", "es", "list"])
    assert code == 2


def test_lang_after_double_dash_is_an_operand():
    from pdftool.cli import resolve_cli_language

    _, rest = resolve_cli_language(["merge", "--", "--lang", "a.pdf"], {})
    assert rest == ["merge", "--", "--lang", "a.pdf"]


def test_explicit_lang_skips_system_detection(monkeypatch):
    calls = []

    def detector():
        calls.append(1)
        return "es-ES"

    monkeypatch.setattr(i18n, "_ui_language", detector)
    _run(["--lang", "en", "list"])
    assert calls == []


def test_help_uses_whole_sentences():
    _code, out, _ = _run(["--lang", "en", "compress", "--help"])
    flat = " ".join(out.split())
    expected = i18n.t(
        "cli.help.with_default",
        help=i18n.t("tool.compress.param.target_mb"),
        value=5.0,
    )
    assert expected in flat
