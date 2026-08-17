from pdftool.core.plugin import BaseParams


class MergeParams(BaseParams):
    """El orden lo decide la lista de inputs. `output_name` es la base del
    archivo de salida (sin extensión), ya sanitizada por la UI; None → default."""

    output_name: str | None = None
