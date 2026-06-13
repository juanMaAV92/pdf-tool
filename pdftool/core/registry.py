from __future__ import annotations

import importlib
import pkgutil

from pdftool.core.plugin import PdfTool

_REGISTRY: dict[str, type[PdfTool]] = {}


def register(cls: type[PdfTool]) -> type[PdfTool]:
    _REGISTRY[cls.meta.id] = cls
    return cls


def clear() -> None:
    _REGISTRY.clear()


def get_tools() -> list[PdfTool]:
    return [cls() for cls in _REGISTRY.values()]


def discover() -> None:
    """Importa cada subpaquete de pdftool.tools para disparar @register."""
    import pdftool.tools as tools_pkg

    for mod in pkgutil.iter_modules(tools_pkg.__path__):
        importlib.import_module(f"pdftool.tools.{mod.name}")
