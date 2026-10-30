from __future__ import annotations

from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class SplitParams(BaseParams):
    """Cómo dividir el PDF.

    - ``ranges``: un PDF por cada rango de ``ranges`` (ej. "1-3, 5, 8-").
    - ``single``: una página por archivo.
    - ``every``: bloques de ``every_n`` páginas.
    """

    mode: Literal["ranges", "single", "every"] = Field(
        default="ranges",
        description="ranges: un PDF por rango; single: una página por archivo; "
        "every: bloques de N páginas.",
    )
    ranges: str = Field(
        default="", description='Rangos de páginas para mode=ranges, ej. "1-3, 5, 8-".'
    )
    every_n: int = Field(
        default=1, ge=1, description="Páginas por archivo para mode=every."
    )
