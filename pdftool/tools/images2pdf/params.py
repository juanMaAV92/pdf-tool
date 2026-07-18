from pydantic import BaseModel


class ImagesToPdfParams(BaseModel):
    """Cada página calca el tamaño de su imagen y van todas en un único PDF,
    en el orden de la lista de inputs. `output_name` es la base del archivo
    de salida (sin extensión), ya sanitizada por la UI; None → default."""

    output_name: str | None = None
