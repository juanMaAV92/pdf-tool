from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable


class JobCancelled(Exception):
    """Señala que el resultado de un job ya no debe continuar."""


@dataclass
class JobHandle:
    """Control cooperativo de un trabajo ejecutado en segundo plano."""

    _cancel_event: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def cancel(self) -> None:
        """Solicita la cancelación; el trabajo se detiene en su próximo progreso."""
        self._cancel_event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _set_thread(self, thread: threading.Thread) -> None:
        self._thread = thread

    def join(self, timeout: float | None = None) -> None:
        """Espera al hilo; útil para tests y cierre controlado."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)


def run_job(work: Callable, on_progress: Callable, on_done: Callable,
            on_error: Callable, *,
            is_current: Callable[[], bool] | None = None) -> JobHandle:
    """Ejecuta `work(on_progress)` en un hilo daemon con cancelación cooperativa.

    `work` recibe el callback de progreso y devuelve un resultado.
    on_done(result) / on_error(exc) se invocan al terminar solo si el job sigue
    vigente. La cancelación se comprueba cada vez que el trabajo reporta avance.
    """
    handle = JobHandle()

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

    thread = threading.Thread(target=_target, daemon=True)
    handle._set_thread(thread)
    thread.start()
    return handle
