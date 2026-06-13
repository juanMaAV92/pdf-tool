from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ToolMeta:
    id: str
    name: str
    description: str
    icon: str
    category: str


@dataclass
class ToolResult:
    outputs: list[Path]
    summary: str


# Reporta avance: fracción 0..1 y un mensaje de estado.
Progress = Callable[[float, str], None]


@dataclass
class ToolContext:
    """Lo que el host presta a cada panel."""
    page: object  # ft.Page (evitamos importar flet en el core)
    run_job: Callable  # (work, on_progress, on_done, on_error) -> None


class PdfTool(ABC):
    meta: ToolMeta

    @abstractmethod
    def build_panel(self, ctx: ToolContext):
        """Devuelve un control Flet con la UI de la herramienta."""
        raise NotImplementedError
