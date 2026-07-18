from pydantic import BaseModel


class ImagesToPdfParams(BaseModel):
    """Sin parámetros: cada imagen (JPG/PNG) se convierte en su propio PDF de
    una página del tamaño exacto de la imagen."""
