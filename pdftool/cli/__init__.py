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
from pdftool.core.plugin import ToolSpec

EXIT_ERROR = 1
EXIT_USAGE = 2


def _build_parser(specs: Sequence[ToolSpec]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
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
        add_params(tool, spec.params)
        tool.add_argument("--json", action="store_true", help="Salida en JSON.")
    return parser


def _spec_to_dict(spec: ToolSpec) -> dict[str, Any]:
    return {
        "id": spec.meta.id,
        "name": spec.meta.name,
        "description": spec.meta.description,
        "category": spec.meta.category,
        "inputs": {
            "min": spec.min_inputs,
            "max": spec.max_inputs,
            "extensions": list(spec.extensions),
        },
        "params": spec.params.model_json_schema(),
    }


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
    try:
        ns = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:  # --help/--version (0) o uso inválido (2)
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    if ns.command == "list":
        return _list(specs, ns.json)
    spec = next(s for s in specs if s.meta.id == ns.command)
    return _run(
        spec,
        ns,
        os.environ if env is None else env,
        sys.stdin if stdin is None else stdin,
    )
