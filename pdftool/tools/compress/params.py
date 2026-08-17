from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class CompressParams(BaseParams):
    target_mb: float = Field(default=5.0, gt=0)
    # "max" conserva el comportamiento actual y es el modo recomendado para
    # el caso habitual: obtener el archivo más pequeño posible.
    mode: Literal["max", "preserve"] = "max"
