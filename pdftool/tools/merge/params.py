from pydantic import Field, field_validator

from pdftool.core.naming import parse_output_name
from pdftool.core.plugin import BaseParams


class MergeParams(BaseParams):
    """El orden lo decide la lista de inputs. `output_name` es la base del
    archivo de salida (sin extensión); None → default."""

    output_name: str | None = Field(
        default=None,
        description="Nombre del PDF unido, sin extensión (por defecto, automático).",
    )

    @field_validator("output_name")
    @classmethod
    def _sanitize(cls, value: str | None) -> str | None:
        # Idempotente: la UI ya lo sanitiza para marcar el campo; la CLI no.
        return parse_output_name(value)
