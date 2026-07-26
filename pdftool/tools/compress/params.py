from pydantic import Field

from pdftool.core.plugin import BaseParams


class CompressParams(BaseParams):
    target_mb: float = Field(default=5.0, gt=0)
