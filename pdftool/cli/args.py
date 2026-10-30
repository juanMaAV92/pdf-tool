"""Traduce los params Pydantic de una herramienta a flags de argparse (sin Flet).

Cada campo `snake_case` se vuelve `--kebab-case`. Lo que no se pasa queda en
None y no llega al modelo, así manda el default de Pydantic. Los campos
secretos (`json_schema_extra={"secret": True}`) nunca son un flag: se leen de
stdin con `--<campo>-stdin` o de la variable `PDFTOOL_<CAMPO>`.
"""

from __future__ import annotations

import argparse
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, TextIO, Union, get_args, get_origin

from pydantic import ValidationError
from pydantic.fields import FieldInfo

from pdftool.core.errors import UserError
from pdftool.core.plugin import BaseParams

_SCALARS = (int, float, str, Path)


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


def _env_var(name: str) -> str:
    return f"PDFTOOL_{name.upper()}"


def _is_secret(field: FieldInfo) -> bool:
    extra = field.json_schema_extra
    return isinstance(extra, dict) and extra.get("secret") is True


def _strip_optional(annotation: Any) -> Any:
    if get_origin(annotation) in (Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _type_kwargs(name: str, annotation: Any) -> dict[str, Any]:
    annotation = _strip_optional(annotation)
    origin = get_origin(annotation)
    if origin is Literal:
        return {"choices": list(get_args(annotation))}
    if origin is tuple:
        items = get_args(annotation)
        if items and all(i in _SCALARS for i in items) and len(set(items)) == 1:
            return {"type": items[0], "nargs": len(items)}
    if annotation in _SCALARS:
        return {"type": annotation}
    raise TypeError(f"Campo {name!r}: tipo {annotation!r} no soportado por la CLI")


def _help(field: FieldInfo) -> str:
    text = field.description or ""
    if not field.is_required() and field.default not in (None, ""):
        default = field.default
        if isinstance(default, tuple):
            default = " ".join(str(v) for v in default)
        text += f" (por defecto: {default})"
    return text


def add_params(parser: argparse.ArgumentParser, params: type[BaseParams]) -> None:
    for name, field in params.model_fields.items():
        if _is_secret(field):
            parser.add_argument(
                f"{_flag(name)}-stdin",
                dest=f"{name}_stdin",
                action="store_true",
                help=f"{field.description or name} Se lee de la primera línea de "
                f"stdin (o de la variable {_env_var(name)}).",
            )
            continue
        parser.add_argument(
            _flag(name),
            dest=name,
            default=None,
            required=field.is_required(),
            help=_help(field),
            **_type_kwargs(name, field.annotation),
        )


def _secret_value(
    name: str, ns: argparse.Namespace, env: Mapping[str, str], stdin: TextIO
) -> str | None:
    if getattr(ns, f"{name}_stdin", False):
        return stdin.readline().rstrip("\r\n")
    return env.get(_env_var(name))


def build_params(
    ns: argparse.Namespace,
    params: type[BaseParams],
    *,
    env: Mapping[str, str],
    stdin: TextIO,
) -> BaseParams:
    values: dict[str, Any] = {}
    for name, field in params.model_fields.items():
        value: Any
        if _is_secret(field):
            value = _secret_value(name, ns, env, stdin)
            if value is None and field.is_required():
                raise UserError(
                    f"Falta {name}: pásalo con {_flag(name)}-stdin "
                    f"o la variable {_env_var(name)}"
                )
        else:
            value = getattr(ns, name, None)
            if isinstance(value, list):
                value = tuple(value)
        if value is not None:
            values[name] = value
    try:
        return params(**values)
    except ValidationError as exc:
        error = exc.errors()[0]
        field_name = str(error["loc"][0]) if error["loc"] else ""
        raise UserError(f"{_flag(field_name)}: {error['msg']}") from exc
