from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field

_MAX_WORKERS = 2
_executor_lock = threading.Lock()
_active_jobs_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None
_log = logging.getLogger("pdftool.jobs")


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


def _notify(callback: Callable, value: object) -> None:
    # Un fallo aquí es un bug de la UI: sin este registro se perdería en un
    # Future que nadie lee y el panel quedaría en «Procesando…».
    try:
        callback(value)
    except Exception:
        _log.exception("Error en el callback de un trabajo")


@dataclass(eq=False)
class _Job:
    """Estado de una ejecución: callbacks, vigencia y ritmo del progreso."""

    handle: JobHandle
    work: Callable
    on_progress: Callable
    on_done: Callable
    on_error: Callable
    is_current: Callable[[], bool] | None
    progress_interval: float
    clock: Callable[[], float]
    _last_progress: float | None = None

    def still_current(self) -> bool:
        if self.handle.cancelled:
            return False
        return self.is_current is None or self.is_current()

    def progress(self, pct: float, message: str) -> None:
        if not self.still_current():
            raise JobCancelled()
        now = self.clock()
        previous = self._last_progress
        if previous is None or pct >= 1.0 or now - previous >= self.progress_interval:
            self._last_progress = now
            self.on_progress(pct, message)

    def run(self) -> None:
        try:
            result = self.work(self.progress)
        except JobCancelled:
            return
        except Exception as exc:  # se reenvía a on_error
            if self.still_current():
                _notify(self.on_error, exc)
        else:
            if self.still_current():
                _notify(self.on_done, result)
        finally:
            _unregister(self.handle)


def run_job(
    work: Callable,
    on_progress: Callable,
    on_done: Callable,
    on_error: Callable,
    *,
    is_current: Callable[[], bool] | None = None,
    progress_interval: float = 0.1,
    clock: Callable[[], float] = time.monotonic,
) -> JobHandle:
    """Ejecuta un trabajo en el executor compartido con cancelación cooperativa.

    `work` recibe el callback de progreso y devuelve un resultado. La cola está
    acotada en concurrencia para no crear un hilo por cada interacción; cancelar
    un handle descarta una tarea pendiente y silencia los callbacks de una tarea
    que ya haya empezado.

    `on_progress` se limita a una llamada cada `progress_interval` segundos
    (cada una cuesta un repintado de la UI); la primera y la final (pct >= 1)
    siempre pasan. La cancelación se comprueba en cada llamada igualmente.
    """
    handle = JobHandle()
    _register(handle)
    job = _Job(
        handle,
        work,
        on_progress,
        on_done,
        on_error,
        is_current,
        progress_interval,
        clock,
    )
    try:
        future = _get_executor().submit(job.run)
    except RuntimeError as exc:
        _unregister(handle)
        if job.still_current():
            on_error(exc)
    else:
        handle._set_future(future)
    return handle
