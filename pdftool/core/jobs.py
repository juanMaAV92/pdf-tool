from __future__ import annotations

import threading
from typing import Callable


def run_job(work: Callable, on_progress: Callable, on_done: Callable,
            on_error: Callable) -> threading.Thread:
    """Ejecuta `work(on_progress)` en un hilo daemon.

    `work` recibe el callback de progreso y devuelve un resultado.
    on_done(result) / on_error(exc) se invocan al terminar.
    """
    def _target() -> None:
        try:
            result = work(on_progress)
        except Exception as exc:  # noqa: BLE001 - se reenvía a on_error
            on_error(exc)
        else:
            on_done(result)

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    return thread
