from pathlib import Path

import flet as ft
import pymupdf
import pytest

from pdftool.core.plugin import ToolContext
from pdftool.tools.organize import panel as panel_module
from pdftool.tools.organize.panel import OrganizeTool


class _Page:
    def __init__(self) -> None:
        self.overlay = []
        self.opened = []
        self.controls_by_id = {}

    def update(self, *_controls) -> None:
        pass

    def open(self, control) -> None:
        self.opened.append(control)

    def get_control(self, control_id):
        return self.controls_by_id[control_id]


class _File:
    def __init__(self, path) -> None:
        self.path = str(path)


class _Event:
    def __init__(self, path) -> None:
        self.files = [_File(path)]


def _pdf(path: Path, pages: int = 4) -> Path:
    with pymupdf.open() as doc:
        for number in range(pages):
            doc.new_page().insert_text((50, 50), f"page {number}")
        doc.save(path)
    return path


@pytest.fixture
def tool(monkeypatch):
    """Panel con trabajos síncronos y sin hilos de miniaturas."""
    monkeypatch.setattr(panel_module, "load_async", lambda *_a, **_k: None)
    panel = OrganizeTool()
    panel.jobs = []

    def run_job(work, on_progress, on_done, on_error, is_current=None):
        panel.jobs.append(work)
        try:
            result = work(lambda *_: None)
        except Exception as exc:
            on_error(exc)
        else:
            on_done(result)

    panel.build_panel(ToolContext(page=_Page(), run_job=run_job))
    return panel


def _open(tool, path):
    tool._on_pick(_Event(path))


def _pages(tool):
    return [page for page, _ in tool._session.plan]


def test_empty_state_has_no_grid_or_toolbar(tool):
    assert not tool._grid.visible
    assert not tool._toolbar.visible
    assert not tool._extract_btn.visible
    assert tool.run_btn.disabled
    assert tool._description.visible


def test_opening_shows_a_cell_per_page_and_a_hint_until_something_changes(
    tool, tmp_path
):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    assert tool._grid.visible
    assert len(tool._grid.controls) == 4
    assert not tool._description.visible
    assert "4 pág." in tool._file_label.value
    assert tool.run_btn.disabled
    assert tool._empty_hint.visible
    assert "Haz algún cambio" in tool._empty_hint.value
    assert [cell.number.value for cell in tool._cells] == ["1", "2", "3", "4"]


def test_a_change_enables_save_and_undo_disables_it_again(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._on_toggle(0)
    tool._rotate_right.on_click(None)
    assert not tool.run_btn.disabled
    assert not tool._empty_hint.visible
    assert not tool._undo_btn.disabled
    tool._undo_btn.on_click(None)
    assert tool.run_btn.disabled
    assert tool._undo_btn.disabled


def test_toolbar_depends_on_the_selection(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    for button in (
        tool._rotate_left,
        tool._rotate_right,
        tool._delete,
        tool._duplicate,
        tool._move_to,
        tool._move_back,
        tool._move_forward,
        tool._extract_btn,
    ):
        assert button.disabled
    assert not tool._reverse.disabled
    tool._on_toggle(0)
    assert not tool._delete.disabled
    assert not tool._extract_btn.disabled
    assert tool._move_back.disabled  # ya es la primera
    assert not tool._move_forward.disabled
    assert tool._counter.value == "1 de 4 seleccionadas"


def test_select_all_checkbox_is_tristate(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    assert tool._select_all.value is False
    tool._on_toggle(0)
    assert tool._select_all.value is None
    tool._select_all.on_change(None)
    assert tool._select_all.value is False
    tool._select_all.on_change(None)
    assert tool._select_all.value is True
    assert all(cell.check.value for cell in tool._cells[:4])


def test_cells_show_position_and_label_the_rotation(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._on_toggle(3)
    tool._rotate_right.on_click(None)
    tool._reverse.on_click(None)
    first = tool._cells[0]
    assert first.number.value == "1"
    assert first.source == 3
    assert first.check.value is True
    assert first.check.semantics_label == "Página 1 de 4, girada 90°"
    assert tool._cells[1].check.semantics_label == "Página 2 de 4"


def test_grid_shrinks_after_deleting(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._on_toggle(0)
    tool._delete.on_click(None)
    assert len(tool._grid.controls) == 3
    assert tool._cells[0].source == 1


def test_deleting_everything_is_blocked_inline(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf", pages=2))
    tool._select_all.on_change(None)
    tool._delete.on_click(None)
    assert "al menos una página" in tool.status.value
    assert _pages(tool) == [1, 2]


def test_save_serializes_the_whole_plan(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._reverse.on_click(None)
    assert tool.make_params().pages == "4-1"


def test_extract_writes_only_the_selection_and_resets(tool, tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    _open(tool, src)
    tool._on_toggle(1)
    tool._on_extract(None)
    with pymupdf.open(tmp_path / "a_páginas.pdf") as doc:
        assert doc.page_count == 1
        assert "page 1" in doc[0].get_text()
    assert not tool._extracting
    # Sigue siendo el plan identidad: Guardar vuelve a estar deshabilitado.
    assert tool.run_btn.disabled


def test_a_file_changed_after_opening_is_refused(tool, tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    _open(tool, src)
    tool._reverse.on_click(None)
    _pdf(src, pages=9)
    jobs = len(tool.jobs)
    tool._on_run_click(None)
    assert "cambió" in tool.status.value
    assert len(tool.jobs) == jobs
    assert not (tmp_path / "a_páginas.pdf").exists()
    assert tool._session is not None  # la edición sigue viva


def test_a_deleted_file_is_reported_and_keeps_the_edit(tool, tmp_path):
    src = _pdf(tmp_path / "a.pdf")
    _open(tool, src)
    tool._reverse.on_click(None)
    src.unlink()
    tool._on_run_click(None)
    assert tool.status.value
    assert _pages(tool) == [4, 3, 2, 1]


def test_too_many_pages_points_to_split(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(panel_module, "MAX_PAGES", 3)
    _open(tool, _pdf(tmp_path / "a.pdf"))
    assert tool._session is None
    assert "Dividir PDF" in tool.status.value
    assert tool._file is None


def test_password_is_rejected_when_choosing(tool, tmp_path):
    src = tmp_path / "locked.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(
            src,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            owner_pw="o",
            user_pw="u",
        )
    _open(tool, src)
    assert tool._session is None
    assert "Proteger PDF" in tool.status.value


def test_choosing_another_pdf_offers_to_restore_changes(tool, tmp_path):
    first = _pdf(tmp_path / "a.pdf")
    second = _pdf(tmp_path / "b.pdf", pages=2)
    _open(tool, first)
    tool._reverse.on_click(None)
    _open(tool, second)
    assert _pages(tool) == [1, 2]
    snack = tool._page.opened[-1]
    assert isinstance(snack, ft.SnackBar)
    assert snack.duration == 8000
    snack.on_action(None)
    assert tool._file == first
    assert _pages(tool) == [4, 3, 2, 1]
    assert len(tool._grid.controls) == 4


def test_choosing_another_pdf_without_changes_says_nothing(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    _open(tool, _pdf(tmp_path / "b.pdf"))
    assert tool._page.opened == []


def test_a_broken_new_file_does_not_lose_the_current_edit(tool, tmp_path):
    first = _pdf(tmp_path / "a.pdf")
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"not a pdf")
    _open(tool, first)
    tool._reverse.on_click(None)
    _open(tool, broken)
    assert tool._file == first
    assert _pages(tool) == [4, 3, 2, 1]
    assert tool.status.value


def test_running_locks_editing_and_pauses_thumbnails(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._on_toggle(0)
    generation = tool._thumbnail_generation
    tool._set_running(True)
    assert tool._delete.disabled
    assert tool._reverse.disabled
    assert tool._thumbnail_generation > generation
    tool._on_toggle(1)
    assert tool._session.selection == {0}
    tool._set_running(False)
    assert not tool._delete.disabled


def test_thumbnails_resume_only_for_what_is_missing(tool, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        panel_module, "load_async", lambda items, *_a, **_k: calls.append(list(items))
    )
    src = _pdf(tmp_path / "a.pdf", pages=3)
    _open(tool, src)
    assert [index for _path, index in calls[-1]] == [0, 1, 2]
    tool._thumbnails[0] = "encoded"
    tool._set_running(True)
    tool._set_running(False)
    assert [index for _path, index in calls[-1]] == [1, 2]


def test_thumbnail_reaches_every_copy_and_failure_shows_broken_icon(
    tool, tmp_path, monkeypatch
):
    captured = {}

    def fake_load(items, on_ready, **_kwargs):
        captured["on_ready"] = on_ready
        captured["path"] = items[0][0]

    monkeypatch.setattr(panel_module, "load_async", fake_load)
    _open(tool, _pdf(tmp_path / "a.pdf", pages=2))
    tool._on_toggle(0)
    tool._duplicate.on_click(None)
    captured["on_ready"]((captured["path"], 0), b"jpeg")
    captured["on_ready"]((captured["path"], 1), None)
    assert tool._cells[0].image.visible and tool._cells[1].image.visible
    assert tool._cells[0].image.src_base64 == tool._cells[1].image.src_base64
    assert not tool._cells[2].image.visible
    assert tool._cells[2].placeholder.name == ft.Icons.BROKEN_IMAGE_OUTLINED


def test_drag_moves_the_page_to_the_last_position(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._page.controls_by_id["source"] = tool._cells[0].control.content
    event = type("E", (), {"src_id": "source"})()
    tool._cells[3].control.on_accept(event)
    assert _pages(tool) == [2, 3, 4, 1]


def test_move_prompt_keeps_the_bar_and_reports_errors_below(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._on_toggle(0)
    tool._move_to.on_click(None)
    assert tool._prompt.visible and not tool._toolbar.visible
    for wrong in ("99", "abc", ""):
        tool._prompt_field.value = wrong
        tool._prompt_apply()
        assert "entre 1 y 4" in tool.status.value
        assert tool._prompt.visible
        assert tool._prompt_field.error_text is None  # no cambia la altura
    tool._prompt_field.value = "3"
    tool._prompt_apply()
    assert _pages(tool) == [2, 3, 1, 4]
    assert not tool._prompt.visible and tool._toolbar.visible


def test_select_prompt_uses_strict_syntax(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._select_btn.on_click(None)
    tool._prompt_field.value = "1-2, 4"
    tool._prompt_apply()
    assert tool._session.selection == {0, 1, 3}
    tool._select_btn.on_click(None)
    tool._prompt_field.value = "3-1"
    tool._prompt_apply()
    assert tool._session.selection == {0, 1, 3}
    assert tool._prompt.visible


def test_result_replaces_the_destination_row_until_the_next_change(tool, tmp_path):
    _open(tool, _pdf(tmp_path / "a.pdf"))
    tool._reverse.on_click(None)
    tool._on_run_click(None)
    assert tool.open_btn.visible
    assert not tool._out_dir.visible
    tool._reverse.on_click(None)
    assert not tool.open_btn.visible
    assert tool._out_dir.visible
