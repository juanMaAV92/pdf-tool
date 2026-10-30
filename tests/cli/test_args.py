import argparse
import io
from pathlib import Path
from typing import Literal

import pytest
from pydantic import Field

from pdftool.cli.args import add_params, build_params
from pdftool.core import registry
from pdftool.core.errors import UserError
from pdftool.core.plugin import BaseParams
from pdftool.tools.compress.params import CompressParams
from pdftool.tools.protect.params import ProtectParams


class _Sample(BaseParams):
    mode: Literal["a", "b"] = Field(default="a", description="Modo.")
    count: int = Field(default=3, ge=1, description="Cuántos.")
    name: str | None = Field(default=None, description="Nombre.")
    color: tuple[float, float, float] = Field(
        default=(0.5, 0.5, 0.5), description="Color."
    )


class _Required(BaseParams):
    text: str = Field(min_length=1, description="Texto.")


def _parse(params, argv, *, env=None, stdin=""):
    parser = argparse.ArgumentParser()
    add_params(parser, params)
    ns = parser.parse_args(argv)
    return build_params(ns, params, env=env or {}, stdin=io.StringIO(stdin))


def test_literal_becomes_choices():
    assert _parse(_Sample, ["--mode", "b"]).mode == "b"
    with pytest.raises(SystemExit) as exc:
        _parse(_Sample, ["--mode", "c"])
    assert exc.value.code == 2


def test_optional_path():
    params = _parse(_Sample, ["--output-dir", "/tmp/salida"])
    assert params.output_dir == Path("/tmp/salida")


def test_tuple_takes_three_floats():
    assert _parse(_Sample, ["--color", "1", "0", "0.2"]).color == (1.0, 0.0, 0.2)


def test_omitted_flags_keep_pydantic_defaults():
    params = _parse(_Sample, [])
    assert (params.mode, params.count, params.name, params.output_dir) == (
        "a",
        3,
        None,
        None,
    )


def test_required_field_is_required():
    assert _parse(_Required, ["--text", "hola"]).text == "hola"
    with pytest.raises(SystemExit) as exc:
        _parse(_Required, [])
    assert exc.value.code == 2


def test_secret_is_never_a_flag():
    parser = argparse.ArgumentParser()
    add_params(parser, ProtectParams)
    flags = {o for action in parser._actions for o in action.option_strings}
    assert "--password" not in flags
    assert "--password-stdin" in flags


def test_secret_from_stdin():
    params = _parse(ProtectParams, ["--password-stdin"], stdin="s3cr3t\n")
    assert params.password == "s3cr3t"


def test_secret_from_env():
    params = _parse(ProtectParams, [], env={"PDFTOOL_PASSWORD": "envpw"})
    assert params.password == "envpw"


def test_missing_secret_is_a_user_error():
    with pytest.raises(UserError, match="--password-stdin"):
        _parse(ProtectParams, [])


def test_validation_error_names_the_flag():
    with pytest.raises(UserError, match="--target-mb"):
        _parse(CompressParams, ["--target-mb", "-1"])


def test_every_real_spec_maps_to_a_parser():
    registry.discover()
    for spec in registry.get_specs():
        add_params(argparse.ArgumentParser(), spec.params)


@pytest.mark.parametrize("reserved", ["json", "inputs", "command", "help", "version"])
def test_reserved_field_names_are_rejected(reserved):
    model = type(
        "Clash",
        (BaseParams,),
        {
            "__annotations__": {reserved: str},
            reserved: Field(default="", description="x"),
        },
    )
    with pytest.raises(TypeError, match=reserved):
        add_params(argparse.ArgumentParser(), model)
