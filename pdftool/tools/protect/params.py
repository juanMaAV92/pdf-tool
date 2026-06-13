from typing import Literal

from pydantic import BaseModel, Field


class ProtectParams(BaseModel):
    mode: Literal["protect", "remove"] = "protect"
    password: str = Field(min_length=1)
