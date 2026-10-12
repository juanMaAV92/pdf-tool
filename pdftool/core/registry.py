from __future__ import annotations

import importlib
import logging
import pkgutil

from pdftool.core.plugin import PdfTool

_REGISTRY: dict[str, type[PdfTool]] = {}
# Todo lo registrado alguna vez, por módulo: `clear()` vacía el registro pero un
# módulo ya importado no vuelve a ejecutar sus @register, así que `discover()`
# los recupera de aquí.
_SEEN: dict[str, list[type[PdfTool]]] = {}
_log = logging.getLogger("pdftool.registry")


def register(cls: type[PdfTool]) -> type[PdfTool]:
    tool_id = cls.meta.id
    current = _REGISTRY.get(tool_id)
    if current is not None and current is not cls:
        raise ValueError(
            f"Id de herramienta duplicado: {tool_id!r} "
            f"({current.__qualname__} y {cls.__qualname__})"
        )
    _REGISTRY[tool_id] = cls
    seen = _SEEN.setdefault(cls.__module__, [])
    if cls not in seen:
        seen.append(cls)
    return cls


def clear() -> None:
    _REGISTRY.clear()


def get_tools() -> list[PdfTool]:
    """Instancias ordenadas por `meta.order` y, a igualdad, por nombre."""
    classes = sorted(_REGISTRY.values(), key=lambda c: (c.meta.order, c.meta.name))
    return [cls() for cls in classes]


def discover(package: str = "pdftool.tools") -> list[str]:
    """Importa cada subpaquete de `package` para disparar @register.

    Una herramienta que falla al importarse se registra en el log y se omite:
    el resto de la app sigue funcionando. Devuelve los nombres que fallaron.
    """
    pkg = importlib.import_module(package)
    failed: list[str] = []
    for mod in pkgutil.iter_modules(pkg.__path__):
        name = f"{package}.{mod.name}"
        try:
            importlib.import_module(name)
        except Exception:
            _log.exception("No se pudo cargar la herramienta %s", mod.name)
            failed.append(mod.name)
    for module, classes in list(_SEEN.items()):
        if module == package or module.startswith(f"{package}."):
            for cls in classes:
                _REGISTRY.setdefault(cls.meta.id, cls)
    return failed
