from __future__ import annotations

import importlib
import logging
import pkgutil

from pdftool.core.plugin import ToolSpec

# Registro de herramientas sin Flet: lo comparten la app y la CLI. Los paneles
# de la app tienen su propio registro en `pdftool.ui.registry`.
_REGISTRY: dict[str, ToolSpec] = {}
# Todo lo registrado alguna vez, por módulo: `clear()` vacía el registro pero un
# módulo ya importado no vuelve a ejecutar su register(), así que `discover()`
# las recupera de aquí.
_SEEN: dict[str, list[ToolSpec]] = {}
_log = logging.getLogger("pdftool.registry")


def register(spec: ToolSpec) -> ToolSpec:
    tool_id = spec.meta.id
    current = _REGISTRY.get(tool_id)
    if current is not None and current is not spec:
        raise ValueError(f"Id de herramienta duplicado: {tool_id!r}")
    _REGISTRY[tool_id] = spec
    module = getattr(spec.run, "__module__", None) or ""
    seen = _SEEN.setdefault(module, [])
    if spec not in seen:
        seen.append(spec)
    return spec


def clear() -> None:
    _REGISTRY.clear()


def get_specs() -> list[ToolSpec]:
    """Specs ordenadas por `meta.order` y, a igualdad, por nombre."""
    return sorted(_REGISTRY.values(), key=lambda s: (s.meta.order, s.meta.id))


def discover(package: str = "pdftool.tools") -> list[str]:
    """Importa el `spec.py` de cada subpaquete de `package` para registrarlo.

    Una herramienta que falla al importarse se registra en el log y se omite.
    Devuelve los nombres que fallaron.
    """
    pkg = importlib.import_module(package)
    failed: list[str] = []
    for mod in pkgutil.iter_modules(pkg.__path__):
        try:
            importlib.import_module(f"{package}.{mod.name}.spec")
        except Exception:
            _log.exception("No se pudo cargar la herramienta %s", mod.name)
            failed.append(mod.name)
    for module, specs in list(_SEEN.items()):
        if module == package or module.startswith(f"{package}."):
            for spec in specs:
                _REGISTRY.setdefault(spec.meta.id, spec)
    return failed
