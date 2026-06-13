import threading

from pdftool.core.jobs import run_job


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
