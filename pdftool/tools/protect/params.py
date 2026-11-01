from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class ProtectParams(BaseParams):
    mode: Literal["protect", "remove"] = Field(
        default="protect",
    )
    # Secreto: la CLI nunca lo acepta como argumento (quedaría en el historial).
    password: str = Field(
        min_length=1,
        json_schema_extra={"secret": True},
    )
