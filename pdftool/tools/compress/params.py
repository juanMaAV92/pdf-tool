from pydantic import BaseModel, Field


class CompressParams(BaseModel):
    target_mb: float = Field(default=5.0, gt=0)
