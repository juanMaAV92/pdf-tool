from pathlib import Path

import pymupdf

from pdftool.core.plugin import FileResult, ToolContext, ToolResult
from pdftool.tools.pdf2images.logic import page_pixels
from pdftool.tools.pdf2images.panel import Pdf2ImagesTool


class _FakePage:
    def __init__(self) -> None:
        self.overlay: list = []

    def update(self) -> None:
        pass


class _FakeEvent:
    def __init__(self, paths: list[str]) -> None:
        self.files = [type("F", (), {"path": p}) for p in paths]


class _Jobs:
    """Ejecuta los trabajos de inmediato y los cuenta."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self, *, work, on_done, on_error, **_kwargs) -> None:
        self.count += 1
        try:
            result = work(lambda *_: None)
        except Exception as exc:
            on_error(exc)
        else:
            on_done(result)


def _tool(jobs=None) -> Pdf2ImagesTool:
    tool = Pdf2ImagesTool()
    tool.build_panel(ToolContext(page=_FakePage(), run_job=jobs or _Jobs()))
    return tool


def _pdf(path: Path) -> Path:
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(path)
    doc.close()
    return path


def test_pixels_appear_after_adding_a_pdf_and_follow_the_resolution(tmp_path):
    tool = _tool()
    assert tool._pixels.visible is False

    tool._on_pick(_FakeEvent([str(_pdf(tmp_path / "a.pdf"))]))

    assert tool._pixels.visible is True
    width, height = page_pixels(pymupdf.Rect(0, 0, 595, 842), 300)
    assert f"{width} × {height}" in tool._pixels.value

    tool._dpi_dd.value = "150"
    tool._on_dpi_change(None)
    width, height = page_pixels(pymupdf.Rect(0, 0, 595, 842), 150)
    assert f"{width} × {height}" in tool._pixels.value


def test_changing_the_resolution_does_not_read_the_file_again(tmp_path):
    jobs = _Jobs()
    tool = _tool(jobs)
    tool._on_pick(_FakeEvent([str(_pdf(tmp_path / "a.pdf"))]))
    assert jobs.count == 1

    tool._dpi_dd.value = "150"
    tool._on_dpi_change(None)
    tool._refresh()
    assert jobs.count == 1


def test_pixels_hide_when_the_list_is_cleared(tmp_path):
    tool = _tool()
    tool._on_pick(_FakeEvent([str(_pdf(tmp_path / "a.pdf"))]))

    tool._remove(0)

    assert tool._pixels.visible is False


def test_pixels_stay_hidden_if_the_file_cannot_be_read(tmp_path):
    broken = tmp_path / "roto.pdf"
    broken.write_bytes(b"no soy un pdf")
    tool = _tool()

    tool._on_pick(_FakeEvent([str(broken)]))

    assert tool._pixels.visible is False


def test_params_come_from_the_dropdowns():
    tool = _tool()
    tool._format_dd.value = "png"
    tool._dpi_dd.value = "150"

    params = tool.make_params()

    assert params.format == "png"
    assert params.dpi == 150


def test_open_folder_opens_the_images_folder_for_one_pdf():
    tool = _tool()
    folder = Path("/a/doc_imágenes")
    result = ToolResult(
        outputs=[folder / "doc_p001.jpg"],
        summary="ok",
        items=[FileResult(Path("/a/doc.pdf"), folder, True, "1 imagen")],
    )

    assert tool.result_folder(result) == folder


def test_open_folder_ignores_failed_files():
    tool = _tool()
    folder = Path("/a/doc_imágenes")
    result = ToolResult(
        outputs=[folder / "doc_p001.jpg"],
        summary="ok",
        items=[
            FileResult(Path("/b/roto.pdf"), None, False, "error"),
            FileResult(Path("/a/doc.pdf"), folder, True, "1 imagen"),
        ],
    )

    assert tool.result_folder(result) == folder
