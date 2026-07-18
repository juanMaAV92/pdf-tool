import logging
from pathlib import Path

import pytest

from pdftool.core import registry
from pdftool.core.plugin import ToolContext, ToolMeta, ToolResult
from pdftool.ui.panel_base import MultiFileToolPanel, SingleFileToolPanel


class _FakePage:
    """Sustituto mínimo de ft.Page para construir paneles en tests."""
    def __init__(self) -> None:
        self.overlay = []

    def update(self) -> None:
        pass


def _tools():
    registry.discover()
    return registry.get_tools()


@pytest.mark.parametrize("tool", _tools(), ids=lambda t: t.meta.id)
def test_panel_builds_and_registers_picker(tool):
    page = _FakePage()
    ctx = ToolContext(page=page, run_job=lambda **kwargs: None)
    control = tool.build_panel(ctx)
    assert control is not None
    assert len(page.overlay) >= 1  # el FilePicker quedó registrado


# ── Contrato de hooks de la base (drive de _on_pick / can_run) ──────────────
# Subclases mínimas NO registradas (no ensucian el registry ni el test de
# arriba). Ejercitan la lógica que el refactor centralizó en la base.

class _FakeFile:
    def __init__(self, path) -> None:
        self.path = path


class _FakeEvent:
    def __init__(self, paths) -> None:
        self.files = [_FakeFile(p) for p in paths]


class _SingleStub(SingleFileToolPanel):
    meta = ToolMeta(id="single-stub", name="S", description="d", icon="", category="c")

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


class _MultiStub(MultiFileToolPanel):
    meta = ToolMeta(id="multi-stub", name="M", description="d", icon="", category="c")
    min_files = 2

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


def _build(tool):
    tool.build_panel(ToolContext(page=_FakePage(), run_job=lambda **kwargs: None))
    return tool


def test_single_file_pick_enables_run():
    tool = _build(_SingleStub())
    assert tool.can_run() is False
    assert tool.run_btn.disabled is True

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool.can_run() is True
    assert tool.run_btn.disabled is False
    assert tool.collect_inputs() == [Path("/tmp/a.pdf")]


def test_single_file_web_mode_without_path_stays_disabled():
    tool = _build(_SingleStub())

    tool._on_pick(_FakeEvent([None]))  # navegador: FilePickerFile sin ruta local

    assert tool.can_run() is False
    assert "navegador" in tool.status.value.lower()


def test_multi_file_requires_min_files():
    tool = _build(_MultiStub())
    assert tool.can_run() is False

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool.can_run() is False  # 1 < min_files(2)
    assert tool.run_btn.disabled is True

    tool._on_pick(_FakeEvent(["/tmp/b.pdf"]))
    assert tool.can_run() is True  # 2 >= min_files
    assert tool.run_btn.disabled is False
    assert tool.collect_inputs() == [Path("/tmp/a.pdf"), Path("/tmp/b.pdf")]


def test_multi_file_ignores_duplicates():
    tool = _build(_MultiStub())

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))  # misma ruta, no se duplica

    assert tool.collect_inputs() == [Path("/tmp/a.pdf")]


def test_on_error_generic_shows_folded_detail():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    assert tool.status.value == "No se pudo procesar el PDF. Puede estar dañado o protegido."
    assert tool._error_toggle.visible is True
    assert tool._error_detail.value == "RuntimeError: boom"
    assert tool._error_detail.visible is False  # arranca plegado


def test_on_error_value_error_has_no_detail_toggle():
    tool = _build(_SingleStub())
    tool._on_error(ValueError("Contraseña incorrecta."))
    assert tool.status.value == "Contraseña incorrecta."
    assert tool._error_toggle.visible is False


def test_toggle_error_detail_reveals_then_hides():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    tool._toggle_error_detail(None)
    assert tool._error_detail.visible is True
    tool._toggle_error_detail(None)
    assert tool._error_detail.visible is False


def test_pick_after_error_clears_stale_detail():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    assert tool._error_toggle.visible is True

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool._error_toggle.visible is False
    assert tool._error_detail.visible is False
    assert tool._error_detail.value == ""


def test_multi_pick_after_error_clears_stale_detail():
    tool = _build(_MultiStub())
    tool._on_error(RuntimeError("boom"))
    assert tool._error_toggle.visible is True

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool._error_toggle.visible is False


def test_on_error_generic_shows_log_button():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    assert tool._log_btn.visible is True


def test_on_error_value_error_hides_log_button():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))       # deja el botón visible
    tool._on_error(ValueError("Contraseña incorrecta."))
    assert tool._log_btn.visible is False


def test_clear_error_hides_log_button():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    tool._clear_error()
    assert tool._log_btn.visible is False


def test_error_actions_row_visibility_tracks_error_state():
    tool = _build(_SingleStub())
    assert tool._error_actions.visible is False

    tool._on_error(RuntimeError("boom"))
    assert tool._error_actions.visible is True

    tool._clear_error()
    assert tool._error_actions.visible is False


def test_on_error_logs_with_traceback(caplog):
    tool = _build(_SingleStub())
    with caplog.at_level(logging.ERROR, logger="pdftool.single-stub"):
        tool._on_error(RuntimeError("boom"))
    assert any(r.exc_info for r in caplog.records)


def test_multi_counter_tracks_files():
    tool = _build(_MultiStub())
    assert tool._counter.value == ""

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool._counter.value == "1 archivo"

    tool._on_pick(_FakeEvent(["/tmp/b.pdf"]))
    assert tool._counter.value == "2 archivos"

    tool._remove(0)
    tool._remove(0)
    assert tool._counter.value == ""


def test_clear_list_disabled_without_files():
    tool = _build(_MultiStub())
    assert tool._clear_btn.disabled is True

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool._clear_btn.disabled is False


def test_clear_list_resets_state():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
    tool._on_error(RuntimeError("boom"))
    tool.open_btn.visible = True

    tool._clear_all(None)

    assert tool.collect_inputs() == []
    assert tool.can_run() is False
    assert tool.run_btn.disabled is True
    assert tool._clear_btn.disabled is True
    assert tool.status.value == ""
    assert tool._error_toggle.visible is False
    assert tool.open_btn.visible is False
    assert tool._counter.value == ""
