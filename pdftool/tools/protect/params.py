from typing import Literal

from pydantic import Field

from pdftool.core.plugin import BaseParams


class ProtectParams(BaseParams):
    mode: Literal["protect", "remove"] = Field(
        default="protect",
        description="protect: añade la contraseña; remove: la quita.",
    )
    # Secreto: la CLI nunca lo acepta como argumento (quedaría en el historial).
    password: str = Field(
        min_length=1,
        description="Contraseña del PDF.",
        json_schema_extra={"secret": True},
    )
