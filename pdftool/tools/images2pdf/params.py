from pydantic import BaseModel


class ImagesToPdfParams(BaseModel):
    """Sin parámetros: cada página calca el tamaño de su imagen y van todas
    en un único PDF, en el orden de la lista de inputs."""
