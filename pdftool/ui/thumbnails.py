from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import TypeVar

from pdftool.core.thumbnails import THUMBNAIL_HEIGHT_PX, render_thumbnail

MISSING = object()  # nunca se intentó (distinto de None = no renderizable)
_CACHE_MAX = 512  # tope duro: ~2-5 MB de RAM; al superarlo expulsa el LRU
_MAX_WORKERS = 2  # renderizar miniaturas es CPU/memoria intensivo

_FLUSH_INTERVAL = 0.1  # s entre repintados de la UI mientras llegan miniaturas

# Clave: ruta, página, alto, mtime y tamaño. Si el archivo cambia en disco, la
# clave cambia y la miniatura antigua deja de servirse.
_Key = tuple[str, int, int, int, int]
_cache: OrderedDict[_Key, bytes | None] = OrderedDict()
_lock = threading.Lock()
_executor_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = ThreadPoolExecutor(
    max_workers=_MAX_WORKERS, thread_name_prefix="pdftool-thumbnail"
)


class ThumbnailTask:
    """Handle de una carga repartida entre los workers de miniaturas."""

    def __init__(self, futures: list[Future]) -> None:
        self._futures = futures

    def cancel(self) -> bool:
        """Cancela lo que aún no empezó; lo que ya empezó coopera vía is_current."""
        return all([f.cancel() for f in self._futures])

    def join(self, timeout: float | None = None) -> None:
        """Espera a todos los trozos (para tests y cierre controlado)."""
        for future in self._futures:
            try:
                future.result(timeout=timeout)
            except TimeoutError:
                return


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_MAX_WORKERS, thread_name_prefix="pdftool-thumbnail"
            )
        return _executor


def shutdown_thumbnail_executor() -> None:
    """Cancela tareas pendientes y libera los workers compartidos."""
    global _executor
    with _executor_lock:
        executor = _executor
        _executor = None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)


def _key(path: Path, page_index: int = 0) -> _Key:
    try:
        st = os.stat(path)
        stamp, size = st.st_mtime_ns, st.st_size
    except OSError:
        stamp, size = -1, -1
    return (str(path), page_index, THUMBNAIL_HEIGHT_PX, stamp, size)


def get_cached(path: Path, page_index: int = 0):
    """bytes | None (cacheado como no-renderizable) | MISSING (nunca intentado)."""
    key = _key(path, page_index)
    with _lock:
        if key not in _cache:
            return MISSING
        _cache.move_to_end(key)
        return _cache[key]


def _store(key: _Key, value: bytes | None) -> None:
    with _lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)


Item = Path | tuple[Path, int]
# El elemento que se pide es el que se devuelve a `on_ready` (ruta o par).
T = TypeVar("T", bound=Item)


def _split(item: Item) -> tuple[Path, int]:
    return item if isinstance(item, tuple) else (item, 0)


def load_async(
    items: Sequence[T],
    on_ready: Callable[[T, bytes | None], None],
    is_current: Callable[[], bool],
    *,
    on_flush: Callable[[], None] | None = None,
) -> ThumbnailTask:
    """Renderiza `items` (rutas o pares (ruta, página)) y notifica cada uno.

    El trabajo se reparte entre los workers de miniaturas. `on_ready` recibe el
    mismo elemento que se pidió; `on_flush`, si se da, se llama como mucho cada
    `_FLUSH_INTERVAL` segundos y al terminar cada trozo, para que la UI repinte
    por lotes y no una vez por miniatura.

    `is_current` es el token de generación del panel: si devuelve False la lista
    cambió y el trabajo termina sin notificar (lo ya renderizado queda en caché).
    """
    chunks = [items[i::_MAX_WORKERS] for i in range(_MAX_WORKERS)]

    def _target(chunk: Sequence[T]) -> None:
        last_flush = time.monotonic()
        pending = False
        for item in chunk:
            if not is_current():
                return
            path, page_index = _split(item)
            value = get_cached(path, page_index)
            if value is MISSING:
                value = render_thumbnail(path, page_index)
                _store(_key(path, page_index), value)
            if not is_current():
                return
            on_ready(item, value)
            pending = True
            now = time.monotonic()
            if on_flush is not None and now - last_flush >= _FLUSH_INTERVAL:
                on_flush()
                last_flush, pending = now, False
        if on_flush is not None and pending and is_current():
            on_flush()

    executor = _get_executor()
    return ThumbnailTask([executor.submit(_target, c) for c in chunks if c])
