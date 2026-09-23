from __future__ import annotations

import threading
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from typing import Callable

_MAX_WORKERS = 2
_executor_lock = threading.Lock()
_active_jobs_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None


class JobCancelled(Exception):
    """Señala que el resultado de un job ya no debe continuar."""


@dataclass(eq=False)
class JobHandle:
    """Control cooperativo de un trabajo ejecutado en segundo plano."""

    _cancel_event: threading.Event = field(default_factory=threading.Event)
    _future: Future | None = None

    def cancel(self) -> None:
        """Cancela una tarea en cola o pide parar una que ya está ejecutándose."""
        self._cancel_event.set()
        if self._future is not None and self._future.cancel():
            _unregister(self)

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _set_future(self, future: Future) -> None:
        self._future = future
        if self.cancelled and future.cancel():
            _unregister(self)

    def join(self, timeout: float | None = None) -> None:
        """Espera al trabajo; útil para tests y cierre controlado."""
        if self._future is None:
            return
        try:
            self._future.result(timeout=timeout)
        except (CancelledError, TimeoutError):
            return


_active_jobs: set[JobHandle] = set()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=_MAX_WORKERS, thread_name_prefix="pdftool-job"
            )
        return _executor


def _register(handle: JobHandle) -> None:
    with _active_jobs_lock:
        _active_jobs.add(handle)


def _unregister(handle: JobHandle) -> None:
    with _active_jobs_lock:
        _active_jobs.discard(handle)


def shutdown_job_executor() -> None:
    """Cancela trabajos pendientes y libera los workers compartidos.

    Los trabajos que ya están dentro de una llamada pesada no se pueden matar de
    forma segura. Conservan la cancelación cooperativa y no volverán a notificar
    a la UI cuando el cierre haya invalidado su handle.
    """
    global _executor
    with _executor_lock:
        executor = _executor
        _executor = None
    with _active_jobs_lock:
        handles = list(_active_jobs)
    for handle in handles:
        handle.cancel()
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)


def run_job(
    work: Callable,
    on_progress: Callable,
    on_done: Callable,
    on_error: Callable,
    *,
    is_current: Callable[[], bool] | None = None,
) -> JobHandle:
    """Ejecuta un trabajo en el executor compartido con cancelación cooperativa.

    `work` recibe el callback de progreso y devuelve un resultado. La cola está
    acotada en concurrencia para no crear un hilo por cada interacción; cancelar
    un handle descarta una tarea pendiente y silencia los callbacks de una tarea
    que ya haya empezado.
    """
    handle = JobHandle()
    _register(handle)

    def _still_current() -> bool:
        return not handle.cancelled and (is_current is None or is_current())

    def _progress(pct: float, message: str) -> None:
        if not _still_current():
            raise JobCancelled()
        on_progress(pct, message)

    def _target() -> None:
        try:
            result = work(_progress)
        except JobCancelled:
            return
        except Exception as exc:  # noqa: BLE001 - se reenvía a on_error
            if _still_current():
                on_error(exc)
        else:
            if _still_current():
                on_done(result)
        finally:
            _unregister(handle)

    try:
        future = _get_executor().submit(_target)
    except RuntimeError as exc:
        _unregister(handle)
        if _still_current():
            on_error(exc)
    else:
        handle._set_future(future)
    return handle
