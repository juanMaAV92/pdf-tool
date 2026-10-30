"""Presenta un `ToolResult` como texto para personas o JSON para agentes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pdftool.core.errors import user_message
from pdftool.core.plugin import FileResult, ToolResult

# Algún archivo del lote falló, pero otros salieron (ver `exit_code`).
EXIT_PARTIAL = 3


def _path(path: Path | None) -> str | None:
    return None if path is None else str(path)


def _item_to_dict(item: FileResult) -> dict[str, Any]:
    return {
        "input": _path(item.input_path),
        "output": _path(item.output_path),
        "ok": item.ok,
        "message": item.message,
        "warnings": list(item.warnings),
        "metrics": dict(item.metrics),
    }


def _all_ok(result: ToolResult) -> bool:
    return all(item.ok for item in result.items or [])


def result_to_dict(tool_id: str, result: ToolResult) -> dict[str, Any]:
    return {
        "ok": _all_ok(result),
        "tool": tool_id,
        "summary": result.summary,
        "outputs": [str(p) for p in result.outputs],
        "items": None
        if result.items is None
        else [_item_to_dict(i) for i in result.items],
        "warnings": list(result.warnings),
        "metrics": dict(result.metrics),
    }


def error_to_dict(tool_id: str | None, exc: BaseException) -> dict[str, Any]:
    message, detail = user_message(exc)
    return {
        "ok": False,
        "tool": tool_id,
        "error": {"message": message, "detail": detail},
    }


def render_text(result: ToolResult) -> str:
    lines = [result.summary]
    if result.items is None:
        lines += [str(p) for p in result.outputs]
    else:
        for item in result.items:
            mark = "✓" if item.ok else "✗"
            lines.append(f"{mark} {item.input_path.name}: {item.message}")
            lines += [f"  aviso: {w}" for w in item.warnings]
    lines += [f"aviso: {w}" for w in result.warnings]
    return "\n".join(lines)


def exit_code(result: ToolResult) -> int:
    return 0 if _all_ok(result) else EXIT_PARTIAL
