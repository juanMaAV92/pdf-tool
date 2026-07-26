from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class ProtectParams(BaseParams):
    mode: Literal["protect", "remove"] = "protect"
    password: str = Field(min_length=1)
