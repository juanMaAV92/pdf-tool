from __future__ import annotations

from pydantic import Field

from pdftool.core.plugin import BaseParams


class OrganizeParams(BaseParams):
    """Las páginas del PDF de salida, en orden (ver `core.pages.parse_plan`)."""

    pages: str = Field(...)
