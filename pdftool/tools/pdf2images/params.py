from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class Pdf2ImagesParams(BaseParams):
    format: Literal["jpg", "png"] = Field(default="jpg")
    dpi: int = Field(default=300, ge=72, le=600)
