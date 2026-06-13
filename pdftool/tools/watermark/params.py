from pydantic import BaseModel, Field


class WatermarkParams(BaseModel):
    text: str = Field(min_length=1)
    opacity: float = Field(default=0.15, gt=0, le=1)
    font_size: int = Field(default=40, gt=0)
    # Color RGB en 0..1 (gris por defecto).
    color: tuple[float, float, float] = (0.5, 0.5, 0.5)
