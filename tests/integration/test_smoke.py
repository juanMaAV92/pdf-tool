import threading
from pathlib import Path

import fitz

from pdftool.core.jobs import run_job
from pdftool.core.plugin import ToolContext
from pdftool.tools.merge.panel import MergeTool


class _Page:
    def __init__(self) -> None:
        self.overlay = []
        self.updates = 0

    def update(self) -> None:
        self.updates += 1


class _File:
    def __init__(self, path: Path) -> None:
        self.path = str(path)


class _PickEvent:
    def __init__(self, paths: list[Path]) -> None:
        self.files = [_File(path) for path in paths]


class _SmokeMergeTool(MergeTool):
    # Las miniaturas tienen pruebas propias; este smoke test valida el flujo
    # de ejecución y evita introducir una segunda fuente de asincronía.
    show_thumbnails = False


def _make_pdf(path: Path, label: str) -> None:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), label)
        document.save(str(path))


def test_merge_panel_runs_real_job_and_writes_real_pdf(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    _make_pdf(first, "first")
    _make_pdf(second, "second")

    finished = threading.Event()

    def run_and_signal(**kwargs):
        original_done = kwargs["on_done"]

        def on_done(result):
            original_done(result)
            finished.set()

        kwargs["on_done"] = on_done
        return run_job(**kwargs)

    page = _Page()
    tool = _SmokeMergeTool()
    tool.build_panel(ToolContext(page=page, run_job=run_and_signal))
    tool._on_pick(_PickEvent([first, second]))

    assert tool.run_btn.disabled is False
    tool.run_btn.on_click(None)

    assert finished.wait(timeout=5)
    output = Path(tool.open_file_btn.data)
    assert output.exists()
    assert tool.open_file_btn.visible is True
    assert "unidos" in tool.status.value

    with fitz.open(str(output)) as document:
        assert document.page_count == 2
