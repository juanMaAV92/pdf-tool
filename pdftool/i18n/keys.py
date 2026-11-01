"""Convenciones de claves compartidas por la app y la CLI."""

from __future__ import annotations


def param_key(tool_id: str | None, field: str) -> str:
    """Ayuda de un parámetro; `tool_id` None para los comunes (`output_dir`)."""
    return f"param.{field}" if tool_id is None else f"tool.{tool_id}.param.{field}"


def choice_key(tool_id: str, field: str, value: str) -> str:
    """Texto de un valor permitido de un parámetro `Literal`."""
    return f"tool.{tool_id}.param.{field}.{value}"
