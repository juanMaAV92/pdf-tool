import logging
import threading
import time

import pytest

from pdftool.core.jobs import JobHandle, run_job, shutdown_job_executor


@pytest.fixture(autouse=True)
def _clean_executor():
    shutdown_job_executor()
    yield
    shutdown_job_executor()


def test_run_job_calls_on_done_with_result():
    done = threading.Event()
    box = {}

    def work(progress):
        progress(0.5, "medio")
        return "RESULT"

    run_job(
        work,
        on_progress=lambda p, m: box.setdefault("prog", (p, m)),
        on_done=lambda r: (box.update(result=r), done.set()),
        on_error=lambda e: (box.update(error=e), done.set()),
    )

    assert done.wait(timeout=5)
    assert box["result"] == "RESULT"
    assert box["prog"] == (0.5, "medio")


def test_run_job_calls_on_error_on_exception():
    done = threading.Event()
    box = {}

    def work(progress):
        raise ValueError("boom")

    run_job(
        work,
        on_progress=lambda p, m: None,
        on_done=lambda r: done.set(),
        on_error=lambda e: (box.update(error=e), done.set()),
    )

    assert done.wait(timeout=5)
    assert isinstance(box["error"], ValueError)


def test_run_job_cancellation_stops_at_next_progress():
    started = threading.Event()
    stopped = threading.Event()
    callbacks = []

    def work(progress):
        started.set()
        try:
            while True:
                progress(0.5, "trabajando")
                time.sleep(0.001)
        finally:
            stopped.set()

    handle = run_job(
        work,
        on_progress=lambda *_: None,
        on_done=lambda _: callbacks.append("done"),
        on_error=lambda _: callbacks.append("error"),
    )

    assert started.wait(timeout=5)
    handle.cancel()
    handle.join(timeout=5)

    assert stopped.is_set()
    assert callbacks == []


def test_run_job_suppresses_callbacks_for_stale_generation():
    callbacks = []
    handle = run_job(
        lambda progress: progress(1.0, "obsoleto"),
        on_progress=lambda *_: callbacks.append("progress"),
        on_done=lambda _: callbacks.append("done"),
        on_error=lambda _: callbacks.append("error"),
        is_current=lambda: False,
    )

    handle.join(timeout=5)

    assert isinstance(handle, JobHandle)
    assert callbacks == []


def test_shared_executor_bounds_parallel_jobs_and_cancels_queue():
    release = threading.Event()
    first_started = threading.Event()
    second_started = threading.Event()
    third_started = threading.Event()

    def blocking(started):
        def work(_progress):
            started.set()
            release.wait(timeout=5)

        return work

    first = run_job(
        blocking(first_started), lambda *_: None, lambda _: None, lambda _: None
    )
    second = run_job(
        blocking(second_started), lambda *_: None, lambda _: None, lambda _: None
    )
    assert first_started.wait(timeout=5)
    assert second_started.wait(timeout=5)

    third = run_job(
        blocking(third_started), lambda *_: None, lambda _: None, lambda _: None
    )
    third.cancel()
    release.set()
    first.join(timeout=5)
    second.join(timeout=5)
    third.join(timeout=5)

    assert not third_started.is_set()


def test_shutdown_cancels_running_job_before_its_next_progress():
    started = threading.Event()
    release = threading.Event()
    callbacks = []

    def work(progress):
        started.set()
        release.wait(timeout=5)
        progress(1.0, "terminado")

    handle = run_job(
        work,
        on_progress=lambda *_: callbacks.append("progress"),
        on_done=lambda _: callbacks.append("done"),
        on_error=lambda _: callbacks.append("error"),
    )
    assert started.wait(timeout=5)

    shutdown_job_executor()
    release.set()
    handle.join(timeout=5)

    assert handle.cancelled
    assert callbacks == []


def test_executor_is_available_again_after_shutdown():
    shutdown_job_executor()
    done = threading.Event()

    handle = run_job(
        lambda _progress: "nuevo trabajo",
        on_progress=lambda *_: None,
        on_done=lambda _: done.set(),
        on_error=lambda _: None,
    )

    assert done.wait(timeout=5)
    handle.join(timeout=5)


class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def job_log():
    handler = _Capture()
    logger = logging.getLogger("pdftool.jobs")
    logger.addHandler(handler)
    yield handler.records
    logger.removeHandler(handler)


def test_failing_on_done_is_logged_and_join_does_not_raise(job_log):
    def on_done(_result):
        raise ZeroDivisionError("bug en la UI")

    handle = run_job(lambda p: "ok", lambda p, m: None, on_done, lambda e: None)
    handle.join(timeout=5)

    assert any(r.exc_info and r.exc_info[0] is ZeroDivisionError for r in job_log)


def test_failing_on_error_is_logged(job_log):
    def work(_p):
        raise ValueError("trabajo")

    def on_error(_exc):
        raise ZeroDivisionError("bug en la UI")

    handle = run_job(work, lambda p, m: None, lambda r: None, on_error)
    handle.join(timeout=5)

    assert any(r.exc_info and r.exc_info[0] is ZeroDivisionError for r in job_log)


def test_progress_is_throttled_but_keeps_first_and_final_updates():
    times = iter([0.0, 0.03, 0.06, 0.12, 0.15, 0.16])
    seen = []
    done = threading.Event()

    def work(progress):
        for pct in (0.1, 0.2, 0.3, 0.4, 0.5, 1.0):
            progress(pct, f"{pct}")
        return "ok"

    handle = run_job(
        work,
        on_progress=lambda p, m: seen.append(p),
        on_done=lambda r: done.set(),
        on_error=lambda e: done.set(),
        progress_interval=0.1,
        clock=lambda: next(times),
    )
    handle.join(timeout=5)
    assert done.is_set()
    assert seen == [0.1, 0.4, 1.0]
