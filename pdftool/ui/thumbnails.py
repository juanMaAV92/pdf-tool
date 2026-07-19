from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path
from typing import Callable

from pdftool.core.thumbnails import THUMBNAIL_HEIGHT_PX, render_thumbnail

MISSING = object()  # nunca se intentó (distinto de None = no renderizable)
_CACHE_MAX = 512    # tope duro: ~2-5 MB de RAM; al superarlo expulsa el LRU

_cache: OrderedDict[tuple[str, int, int], bytes | None] = OrderedDict()
_lock = threading.Lock()


def get_cached(path: Path, page_index: int = 0):
    """bytes | None (cacheado como no-renderizable) | MISSING (nunca intentado)."""
    key = (str(path), page_index, THUMBNAIL_HEIGHT_PX)
    with _lock:
        if key not in _cache:
            return MISSING
        _cache.move_to_end(key)
        return _cache[key]


def _store(key: tuple[str, int, int], value: bytes | None) -> None:
    with _lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


def load_async(paths: list[Path],
               on_ready: Callable[[Path, bytes | None], None],
               is_current: Callable[[], bool]) -> threading.Thread:
    """Renderiza `paths` en un hilo daemon y notifica on_ready(path, png | None).

    `is_current` es el token de generación del panel: si devuelve False la lista
    cambió y el hilo termina sin notificar (lo ya renderizado queda en caché).

    Dos hilos concurrentes pueden renderizar el mismo path si se cruzan antes de
    que el primero escriba en caché: CPU desperdiciada, nunca corrupción
    (`_store` es idempotente y con lock).
    """
    def _target() -> None:
        for path in paths:
            if not is_current():
                return
            value = get_cached(path)
            if value is MISSING:
                value = render_thumbnail(path)
                _store((str(path), 0, THUMBNAIL_HEIGHT_PX), value)
            if not is_current():
                return
            on_ready(path, value)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    return thread
