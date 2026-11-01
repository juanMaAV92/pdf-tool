from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from pdftool.core.config import Settings
from pdftool.i18n import t


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
    """Identidad de una herramienta. Los textos salen del diccionario
    (`tool.<id>.name`, `tool.<id>.description`, `category.<category>`) y se
    resuelven al leerse, en el idioma activo."""

    id: str
    # Id estable de la categoría (organize, optimize, convert, edit, security).
    category: str
    # Posición en la navegación (menor primero); a igualdad, por id.
    order: int = 100

    @property
    def name(self) -> str:
        return t(f"tool.{self.id}.name")

    @property
    def description(self) -> str:
        return t(f"tool.{self.id}.description")

    @property
    def category_label(self) -> str:
        return t(f"category.{self.category}")


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

    # Ayuda: `param.output_dir` en el diccionario.
    output_dir: Path | None = Field(default=None)


@dataclass(frozen=True)
class ToolSpec:
    """Definición de una herramienta sin UI: la comparten la app y la CLI."""

    meta: ToolMeta
    params: type[BaseParams]
    # run(inputs: list[Path], params, progress=...) -> ToolResult
    run: Callable[..., ToolResult]
    # Reglas de entrada que comparten la app y la CLI: cuántos archivos
    # (max None = sin límite) y con qué extensiones.
    min_inputs: int = 1
    max_inputs: int | None = None
    extensions: tuple[str, ...] = ("pdf",)


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
