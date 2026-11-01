"""Nombres, categorías y ayuda de parámetros salen del diccionario."""

import io
import json
import typing

import pytest

from pdftool import i18n
from pdftool.cli import main
from pdftool.core import registry


def _specs():
    registry.discover()
    return [
        s for s in registry.get_specs() if s.run.__module__.startswith("pdftool.tools.")
    ]


def _keys(code: str) -> set[str]:
    path = i18n.LOCALES_DIR / f"{code}.json"
    return set(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("code", ["en", "es"])
def test_every_tool_has_name_description_and_category(code):
    keys = _keys(code)
    for spec in _specs():
        tid = spec.meta.id
        assert f"tool.{tid}.name" in keys, tid
        assert f"tool.{tid}.description" in keys, tid
        assert f"category.{spec.meta.category}" in keys, tid


@pytest.mark.parametrize("code", ["en", "es"])
def test_every_param_and_literal_value_has_text(code):
    keys = _keys(code)
    assert "param.output_dir" in keys
    for spec in _specs():
        tid = spec.meta.id
        for name, field in spec.params.model_fields.items():
            if name == "output_dir":
                continue
            assert f"tool.{tid}.param.{name}" in keys, (tid, name)
            if typing.get_origin(field.annotation) is typing.Literal:
                for value in typing.get_args(field.annotation):
                    assert f"tool.{tid}.param.{name}.{value}" in keys, (tid, value)


def _run(argv):
    out = io.StringIO()
    from contextlib import redirect_stdout

    with redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


def test_cli_list_json_follows_language():
    _, out = _run(["--lang", "en", "list", "--json"])
    merge = next(t for t in json.loads(out) if t["id"] == "merge")
    assert merge["name"] == "Merge PDFs"
    assert merge["category"] == "Organize"
    assert set(merge) == {"id", "name", "description", "category", "inputs", "params"}
    compress = next(t for t in json.loads(out) if t["id"] == "compress")
    target = compress["params"]["properties"]["target_mb"]["description"]
    assert target == i18n.t("tool.compress.param.target_mb")
    assert "Tamaño" not in out

    _, out = _run(["--lang", "es", "list", "--json"])
    merge = next(t for t in json.loads(out) if t["id"] == "merge")
    assert merge["name"] == "Unir PDFs"
    assert merge["category"] == "Organizar"


def test_cli_help_follows_language():
    code, out = _run(["--lang", "en", "compress", "--help"])
    assert code == 0
    assert i18n.t("tool.compress.param.target_mb") in " ".join(out.split())
    assert i18n.t("tool.compress.param.mode.preserve") in " ".join(out.split())
