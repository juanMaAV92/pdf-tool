from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from pdftool.core.config import Settings


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
    # Etiqueta corta por salida (misma longitud/orden que outputs), para mostrar
    # el resultado junto a cada archivo. None si no aplica (p. ej. 1 archivo).
    details: list[str] | None = None


class BaseParams(BaseModel):
    """Campos comunes a toda ejecución.

    `output_dir` None → la salida va junto al archivo de entrada (el default de
    siempre); una ruta → todas las salidas van a esa carpeta.
    """

    output_dir: Path | None = None


# Reporta avance: fracción 0..1 y un mensaje de estado.
Progress = Callable[[float, str], None]


@dataclass
class ToolContext:
    """Lo que el host presta a cada panel."""
    page: object  # ft.Page (evitamos importar flet en el core)
    run_job: Callable  # (work, on_progress, on_done, on_error) -> None
    settings: Settings | None = None


class PdfTool(ABC):
    meta: ToolMeta

    @abstractmethod
    def build_panel(self, ctx: ToolContext):
        """Devuelve un control Flet con la UI de la herramienta."""
        raise NotImplementedError
