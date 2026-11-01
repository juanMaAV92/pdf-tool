"""`pdf-tool`: las herramientas de la app como línea de comandos (sin Flet).

Los subcomandos salen del registro de specs y sus flags, de los params de cada
herramienta: una herramienta nueva aparece aquí sin tocar este módulo.
Códigos de salida: 0 ok · 1 error al procesar · 2 uso o params inválidos ·
3 lote parcial (algún archivo falló).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO

from pdftool import __version__
from pdftool.cli.args import add_params, build_params
from pdftool.cli.report import error_to_dict, exit_code, render_text, result_to_dict
from pdftool.core import registry
from pdftool.core.errors import UserError, user_message
from pdftool.core.plugin import BaseParams, ToolSpec
from pdftool.i18n import param_help

EXIT_ERROR = 1
EXIT_USAGE = 2


class _UsageError(Exception):
    def __init__(self, message: str, usage: str) -> None:
        super().__init__(message)
        self.usage = usage


class _Parser(argparse.ArgumentParser):
    """Un uso inválido lanza en vez de salir: así `--json` también lo reporta
    en JSON. Los subcomandos heredan esta clase."""

    def error(self, message: str):  # type: ignore[override]
        raise _UsageError(f"{self.prog}: {message}", self.format_usage())


def _build_parser(specs: Sequence[ToolSpec]) -> argparse.ArgumentParser:
    parser = _Parser(
        prog="pdf-tool",
        description="Herramientas locales para PDFs: nada sale de tu equipo.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMANDO")
    listing = sub.add_parser("list", help="Lista las herramientas disponibles.")
    listing.add_argument("--json", action="store_true", help="Salida en JSON.")
    for spec in specs:
        tool = sub.add_parser(
            spec.meta.id, help=spec.meta.name, description=spec.meta.description
        )
        tool.add_argument(
            "inputs",
            nargs="+",
            type=Path,
            metavar="ARCHIVO",
            help="Archivos de entrada (" + ", ".join(spec.extensions) + ").",
        )
        add_params(tool, spec.params, spec.meta.id)
        tool.add_argument("--json", action="store_true", help="Salida en JSON.")
    return parser


def _spec_to_dict(spec: ToolSpec) -> dict[str, Any]:
    return {
        "id": spec.meta.id,
        "name": spec.meta.name,
        "description": spec.meta.description,
        "category": spec.meta.category_label,
        "inputs": {
            "min": spec.min_inputs,
            "max": spec.max_inputs,
            "extensions": list(spec.extensions),
        },
        "params": _params_schema(spec),
    }


def _params_schema(spec: ToolSpec) -> dict[str, Any]:
    """Esquema JSON de los params con las descripciones del idioma activo."""
    schema = spec.params.model_json_schema()
    # El docstring de la clase es documentación para desarrolladores.
    schema.pop("description", None)
    common = set(BaseParams.model_fields)
    for name, prop in schema.get("properties", {}).items():
        prop["description"] = param_help(None if name in common else spec.meta.id, name)
    return schema


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _list(specs: Sequence[ToolSpec], as_json: bool) -> int:
    if as_json:
        _print_json([_spec_to_dict(s) for s in specs])
    else:
        for s in specs:
            print(f"{s.meta.id:<11} {s.meta.name} — {s.meta.description}")
    return 0


def _check_inputs(spec: ToolSpec, inputs: list[Path]) -> list[Path]:
    n = len(inputs)
    if n < spec.min_inputs:
        raise UserError(f"{spec.meta.id} necesita al menos {spec.min_inputs} archivos")
    if spec.max_inputs is not None and n > spec.max_inputs:
        raise UserError(
            f"{spec.meta.id} acepta como máximo {spec.max_inputs} archivo(s)"
        )
    for path in inputs:
        if not path.exists():
            raise UserError(f"No existe: {path}")
        if not path.is_file():
            raise UserError(f"No es un archivo: {path}")
        if path.suffix.lower().lstrip(".") not in spec.extensions:
            expected = ", ".join(f".{e}" for e in spec.extensions)
            raise UserError(f"{path.name}: se espera {expected}")
    return [path.resolve() for path in inputs]


def _fail(spec: ToolSpec, exc: BaseException, as_json: bool, code: int) -> int:
    if as_json:
        _print_json(error_to_dict(spec.meta.id, exc))
    else:
        message, detail = user_message(exc)
        print(f"pdf-tool: {message}", file=sys.stderr)
        if detail is not None:
            print(f"detalle: {detail}", file=sys.stderr)
    return code


def _run(spec: ToolSpec, ns: argparse.Namespace, env, stdin) -> int:
    try:
        inputs = _check_inputs(spec, ns.inputs)
        params = build_params(ns, spec.params, env=env, stdin=stdin)
        if params.output_dir is not None and not params.output_dir.is_dir():
            raise UserError(f"No existe la carpeta de salida: {params.output_dir}")
    except UserError as exc:
        return _fail(spec, exc, ns.json, EXIT_USAGE)
    try:
        result = spec.run(inputs, params)
    except Exception as exc:
        return _fail(spec, exc, ns.json, EXIT_ERROR)
    if ns.json:
        _print_json(result_to_dict(spec.meta.id, result))
    else:
        print(render_text(result))
    return exit_code(result)


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    # La lógica registra avisos por lote; sin handler, Python los escribiría
    # en stderr y ensuciaría la salida. El resultado ya los reporta.
    logging.getLogger("pdftool").addHandler(logging.NullHandler())
    registry.discover()
    specs = registry.get_specs()
    parser = _build_parser(specs)
    args = sys.argv[1:] if argv is None else argv
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:  # --help/--version
        return exc.code if isinstance(exc.code, int) else 0
    except _UsageError as exc:
        if "--json" in args:
            tool_id = next((a for a in args if a in {s.meta.id for s in specs}), None)
            _print_json(error_to_dict(tool_id, UserError(str(exc))))
        else:
            print(f"{exc.usage}{exc}", file=sys.stderr)
        return EXIT_USAGE
    if ns.command == "list":
        return _list(specs, ns.json)
    spec = next(s for s in specs if s.meta.id == ns.command)
    return _run(
        spec,
        ns,
        os.environ if env is None else env,
        sys.stdin if stdin is None else stdin,
    )
