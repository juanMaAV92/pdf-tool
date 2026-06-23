from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SplitParams(BaseModel):
    """Cómo dividir el PDF.

    - ``ranges``: un PDF por cada rango de ``ranges`` (ej. "1-3, 5, 8-").
    - ``single``: una página por archivo.
    - ``every``: bloques de ``every_n`` páginas.
    """

    mode: Literal["ranges", "single", "every"] = "ranges"
    ranges: str = ""
    every_n: int = Field(default=1, ge=1)
