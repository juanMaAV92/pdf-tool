from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from collections import OrderedDict
from pathlib import Path
from typing import Callable

from pdftool.core.thumbnails import THUMBNAIL_HEIGHT_PX, render_thumbnail

MISSING = object()  # nunca se intentó (distinto de None = no renderizable)
_CACHE_MAX = 512    # tope duro: ~2-5 MB de RAM; al superarlo expulsa el LRU
_MAX_WORKERS = 2    # renderizar miniaturas es CPU/memoria intensivo

_cache: OrderedDict[tuple[str, int, int], bytes | None] = OrderedDict()
_lock = threading.Lock()
_executor_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = ThreadPoolExecutor(
    max_workers=_MAX_WORKERS, thread_name_prefix="pdftool-thumbnail")


class ThumbnailTask:
    """Handle pequeño compatible con el antiguo `Thread.join()` de la UI."""

    def __init__(self, future: Future) -> None:
        self._future = future

    def cancel(self) -> bool:
        """Cancela el trabajo si aún no empezó; el loop coopera si ya empezó."""
        return self._future.cancel()

    def join(self, timeout: float | None = None) -> None:
        """Espera al trabajo; mantiene la API usada por los tests existentes."""
        try:
            self._future.result(timeout=timeout)
        except TimeoutError:
            return


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_MAX_WORKERS, thread_name_prefix="pdftool-thumbnail")
        return _executor


def shutdown_thumbnail_executor() -> None:
    """Cancela tareas pendientes y libera los workers compartidos."""
    global _executor
    with _executor_lock:
        executor = _executor
        _executor = None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)


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
               is_current: Callable[[], bool]) -> ThumbnailTask:
    """Renderiza `paths` en un worker compartido y notifica cada resultado.

    `is_current` es el token de generación del panel: si devuelve False la lista
    cambió y el trabajo termina sin notificar (lo ya renderizado queda en caché).
    El executor limita el número de renders simultáneos; una tarea que ya empezó
    se detiene cooperativamente en el siguiente archivo.
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

    future = _get_executor().submit(_target)
    return ThumbnailTask(future)
