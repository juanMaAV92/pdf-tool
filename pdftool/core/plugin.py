from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from pdftool.core.config import Settings


@dataclass(frozen=True)
class FileResult:
    """Resultado estructurado de una entrada individual de un lote."""

    input_path: Path
    output_path: Path | None
    ok: bool
    message: str
    # Avisos para el usuario (p. ej. «se rasterizaron páginas») y cifras del
    # resultado (p. ej. original_mb, final_mb, saved_pct) sin parsear texto.
    warnings: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolMeta:
    id: str
    name: str
    description: str
    category: str
    # Posición en la navegación (menor primero); a igualdad, por nombre.
    order: int = 100


@dataclass
class ToolResult:
    outputs: list[Path]
    summary: str
    # Resultados por entrada para herramientas por lote. None si no aplica
    # (p. ej. una herramienta de archivo único).
    items: list[FileResult] | None = None
    # Avisos del run completo (se muestran bajo el resumen) y cifras agregadas.
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


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
