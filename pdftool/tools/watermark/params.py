from typing import Annotated

from pydantic import Field

from pdftool.core.plugin import BaseParams

# Componente de color RGB.
_Unit = Annotated[float, Field(ge=0, le=1)]


class WatermarkParams(BaseParams):
    text: str = Field(min_length=1)
    opacity: float = Field(default=0.15, gt=0, le=1)
    font_size: int = Field(default=40, gt=0)
    color: tuple[_Unit, _Unit, _Unit] = Field(default=(0.5, 0.5, 0.5))
