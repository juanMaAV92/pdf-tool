import threading
import time

from pdftool.core.jobs import JobHandle, run_job


def test_run_job_calls_on_done_with_result():
    done = threading.Event()
    box = {}

    def work(progress):
        progress(0.5, "medio")
        return "RESULT"

    run_job(work,
            on_progress=lambda p, m: box.setdefault("prog", (p, m)),
            on_done=lambda r: (box.update(result=r), done.set()),
            on_error=lambda e: (box.update(error=e), done.set()))

    assert done.wait(timeout=5)
    assert box["result"] == "RESULT"
    assert box["prog"] == (0.5, "medio")


def test_run_job_calls_on_error_on_exception():
    done = threading.Event()
    box = {}

    def work(progress):
        raise ValueError("boom")

    run_job(work,
            on_progress=lambda p, m: None,
            on_done=lambda r: done.set(),
            on_error=lambda e: (box.update(error=e), done.set()))

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

    handle = run_job(work,
                     on_progress=lambda *_: None,
                     on_done=lambda _: callbacks.append("done"),
                     on_error=lambda _: callbacks.append("error"))

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
