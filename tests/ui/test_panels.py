import logging
from pathlib import Path

import flet as ft
import pymupdf
import pytest

from pdftool.core.errors import GENERIC_MESSAGE, UserError
from pdftool.core.jobs import JobHandle
from pdftool.core.plugin import (
    BaseParams,
    FileResult,
    ToolContext,
    ToolMeta,
    ToolResult,
)
from pdftool.ui import registry
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import SingleFileToolPanel


class _FakePage:
    """Sustituto mínimo de ft.Page para construir paneles en tests."""

    def __init__(self) -> None:
        self.overlay = []
        self.opened = []

    def update(self) -> None:
        pass

    def open(self, control) -> None:
        self.opened.append(control)


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
    meta = ToolMeta(id="single-stub", category="c")

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


class _RunnableStub(SingleFileToolPanel):
    meta = ToolMeta(id="runnable-stub", category="c")

    def make_params(self):
        return BaseParams()

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


class _MultiStub(MultiFileToolPanel):
    meta = ToolMeta(id="multi-stub", category="c")
    min_files = 2

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


def _sync_run_job(work, on_progress, on_done, on_error, is_current=None):
    """run_job inmediato: ejecuta el trabajo en el hilo del test."""
    try:
        result = work(on_progress)
    except Exception as exc:
        on_error(exc)
    else:
        on_done(result)
    return JobHandle()


def _build(tool):
    tool.build_panel(ToolContext(page=_FakePage(), run_job=lambda **kwargs: None))
    return tool


def test_single_file_pick_enables_run():
    tool = _build(_SingleStub())
    assert tool.can_run() is False
    assert tool.run_btn.disabled is True
    assert tool._empty_hint.visible is True
    assert tool._empty_hint.value == "Añade un archivo para continuar."
    assert tool._body.expand is False

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool.can_run() is True
    assert tool.run_btn.disabled is False
    assert tool._empty_hint.visible is False
    assert tool._body.expand is False
    assert tool.collect_inputs() == [Path("/tmp/a.pdf")]


def test_single_file_web_mode_without_path_stays_disabled():
    tool = _build(_SingleStub())

    tool._on_pick(_FakeEvent([None]))  # navegador: FilePickerFile sin ruta local

    assert tool.can_run() is False
    assert "navegador" in tool.status.value.lower()


def _running(tool, page=None):
    calls = {}
    handle = JobHandle()

    def fake_run_job(**kwargs):
        calls.update(kwargs)
        return handle

    ctx = ToolContext(page=page or _FakePage(), run_job=fake_run_job)
    tool.build_panel(ctx)
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool.run_btn.on_click(None)
    return ctx, calls, handle


def test_returning_to_a_panel_keeps_the_running_job_and_its_result():
    tool = _RunnableStub()
    ctx, calls, handle = _running(tool)
    first = tool._root

    again = tool.build_panel(ctx)  # navegar fuera y volver

    assert again is first
    assert handle.cancelled is False
    assert tool.collect_inputs() == [Path("/tmp/a.pdf")]
    calls["on_done"](ToolResult(outputs=[Path("/tmp/a_x.pdf")], summary="Listo"))
    assert tool.status.value == "Listo"
    assert tool.open_file_btn.visible is True


def test_returning_to_a_batch_panel_keeps_the_file_list():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
    tool.build_panel(tool._ctx)
    assert tool.collect_inputs() == [Path("/tmp/a.pdf"), Path("/tmp/b.pdf")]
    assert len(tool._file_list.controls) == 2


def test_a_new_page_rebuilds_the_panel_and_cancels_the_old_job():
    tool = _RunnableStub()
    _ctx, calls, handle = _running(tool)
    old_done = calls["on_done"]

    tool.build_panel(ToolContext(page=_FakePage(), run_job=lambda **kw: None))
    old_done(ToolResult(outputs=[Path("/tmp/old.pdf")], summary="antiguo"))

    assert handle.cancelled is True
    assert tool.status.value == ""
    assert tool.open_btn.visible is False


# ── Cancelar ─────────────────────────────────────────────────────────────────


def test_cancel_button_is_visible_only_while_running():
    tool = _RunnableStub()
    assert _build(tool).cancel_btn.visible is False
    _ctx, calls, _handle = _running(tool)
    assert tool.cancel_btn.visible is True
    calls["on_done"](ToolResult(outputs=[], summary="Listo"))
    assert tool.cancel_btn.visible is False


def test_cancel_stops_the_job_and_ignores_its_late_result():
    tool = _RunnableStub()
    _ctx, calls, handle = _running(tool)

    tool.cancel_btn.on_click(None)

    assert handle.cancelled is True
    assert tool.cancel_btn.visible is False
    assert tool.progress.visible is False
    assert tool.run_btn.disabled is False
    assert "Cancelado" in tool.status.value
    assert "terminados se conservan" in tool.status.value
    calls["on_done"](ToolResult(outputs=[Path("/tmp/x.pdf")], summary="tarde"))
    assert "Cancelado" in tool.status.value


def test_error_hides_the_cancel_button():
    tool = _RunnableStub()
    _ctx, calls, _handle = _running(tool)
    calls["on_error"](RuntimeError("boom"))
    assert tool.cancel_btn.visible is False


def test_multi_file_requires_min_files():
    tool = _build(_MultiStub())
    assert tool.can_run() is False
    assert tool._empty_hint.value == "Añade al menos 2 archivos para continuar."
    assert tool._body.expand is False

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool.can_run() is False  # 1 < min_files(2)
    assert tool.run_btn.disabled is True
    assert tool._empty_hint.value == "Añade 1 archivo más para continuar."
    assert tool._body.expand is False

    tool._on_pick(_FakeEvent(["/tmp/b.pdf"]))
    assert tool.can_run() is True  # 2 >= min_files
    assert tool.run_btn.disabled is False
    assert tool._empty_hint.visible is False
    assert tool._body.expand is True
    assert tool.collect_inputs() == [Path("/tmp/a.pdf"), Path("/tmp/b.pdf")]


def test_multi_file_ignores_duplicates():
    tool = _build(_MultiStub())

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))  # misma ruta, no se duplica

    assert tool.collect_inputs() == [Path("/tmp/a.pdf")]


def test_on_error_generic_shows_folded_detail():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    assert tool.status.value == GENERIC_MESSAGE
    assert tool._error_toggle.visible is True
    assert tool._error_detail.value == "RuntimeError: boom"
    assert tool._error_detail.visible is False  # arranca plegado


def test_on_error_value_error_has_no_detail_toggle():
    tool = _build(_SingleStub())
    tool._on_error(UserError("Contraseña incorrecta."))
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
    tool._on_error(RuntimeError("boom"))  # deja el botón visible
    tool._on_error(UserError("Contraseña incorrecta."))
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


def test_open_file_button_visible_only_for_single_output():
    tool = _build(_SingleStub())
    assert tool.open_file_btn.visible is False

    tool._show_result_actions(ToolResult(outputs=[Path("/tmp/a.pdf")], summary="ok"))
    assert tool.open_file_btn.visible is True
    assert tool.open_file_btn.data == Path("/tmp/a.pdf")
    assert tool.open_btn.visible is True

    tool._show_result_actions(
        ToolResult(outputs=[Path("/tmp/a.pdf"), Path("/tmp/b.pdf")], summary="ok")
    )
    assert tool.open_file_btn.visible is False
    assert tool.open_btn.visible is True
    assert tool.open_btn.style is None  # abrir carpeta prima si hay varias salidas


def test_open_file_button_hides_on_new_pick():
    tool = _build(_SingleStub())
    tool._show_result_actions(ToolResult(outputs=[Path("/tmp/a.pdf")], summary="ok"))

    tool._on_pick(_FakeEvent(["/tmp/b.pdf"]))

    assert tool.open_file_btn.visible is False
    assert tool.open_btn.visible is False


def test_result_actions_are_grouped_below_summary():
    tool = _build(_RunnableStub())
    assert tool._result_actions.visible is False
    assert tool._feedback.controls[:4] == [
        tool.progress,
        tool._status_row,
        tool._warnings,
        tool._result_actions,
    ]
    assert tool._status_row.controls == [tool._status_icon, tool.status]
    assert tool._result_actions.wrap is True

    tool._show_result_actions(ToolResult(outputs=[Path("/tmp/a.pdf")], summary="ok"))
    assert tool._result_actions.visible is True
    assert isinstance(tool.open_file_btn, ft.FilledButton)
    assert tool.run_btn.style is not None

    tool._on_pick(_FakeEvent(["/tmp/b.pdf"]))
    assert tool._result_actions.visible is False
    assert tool.run_btn.style is None


def test_retry_clears_previous_summary_and_result_actions():
    calls = {}
    tool = _RunnableStub()
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool.run_btn.on_click(None)
    calls["on_done"](ToolResult(outputs=[Path("/tmp/out.pdf")], summary="Listo"))
    assert tool.status.value == "Listo"

    tool.run_btn.on_click(None)
    assert tool.status.value == "Procesando…"
    assert tool._result_actions.visible is False
    assert tool.progress.visible is True
    calls["on_error"](RuntimeError("boom"))
    assert tool._log_btn.visible is True
    assert tool._error_actions in tool._feedback.controls


def test_result_without_outputs_does_not_offer_open_actions():
    tool = _build(_RunnableStub())
    tool._show_result_actions(ToolResult(outputs=[], summary="Sin archivos"))
    assert tool._result_actions.visible is False
    assert tool.open_btn.visible is False
    assert tool.open_file_btn.visible is False


def test_watermark_opacity_is_shown_as_a_percentage():
    from pdftool.tools.watermark.panel import WatermarkTool

    tool = _build(WatermarkTool())
    assert (tool._opacity.min, tool._opacity.max, tool._opacity.value) == (5, 60, 15)
    assert tool._opacity.label == "{value} %"
    assert tool.make_params().opacity == 0.15


def test_compress_defaults_to_max_mode_with_tooltip():
    from pdftool.tools.compress.panel import CompressTool

    tool = _build(CompressTool())

    assert tool._mode_dd.value == "max"
    assert "archivo más pequeño" in tool._mode_help.tooltip
    assert "texto y enlaces" in tool._mode_help.tooltip


def test_multi_row_paths_map_successes_to_outputs():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf", "/tmp/c.pdf"]))

    tool.on_result(
        ToolResult(
            outputs=[Path("/tmp/a_x.pdf"), Path("/tmp/c_x.pdf")],
            summary="2 de 3 PDFs procesados",
            items=[
                FileResult(Path("/tmp/a.pdf"), Path("/tmp/a_x.pdf"), True, "→ a_x.pdf"),
                FileResult(Path("/tmp/b.pdf"), None, False, "Contraseña incorrecta."),
                FileResult(Path("/tmp/c.pdf"), Path("/tmp/c_x.pdf"), True, "→ c_x.pdf"),
            ],
        )
    )

    assert tool._row_paths == [Path("/tmp/a_x.pdf"), None, Path("/tmp/c_x.pdf")]


def test_multi_row_paths_cleared_with_results():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
    tool.on_result(
        ToolResult(
            outputs=[Path("/tmp/a_x.pdf"), Path("/tmp/b_x.pdf")],
            summary="2 PDFs",
            items=[
                FileResult(Path("/tmp/a.pdf"), Path("/tmp/a_x.pdf"), True, "→ a_x.pdf"),
                FileResult(Path("/tmp/b.pdf"), Path("/tmp/b_x.pdf"), True, "→ b_x.pdf"),
            ],
        )
    )
    assert tool._row_paths != []

    tool._clear_all(None)

    assert tool._row_paths == []


def test_multi_row_paths_positional_when_no_failures():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))

    tool.on_result(
        ToolResult(
            outputs=[Path("/tmp/a_2mb.pdf"), Path("/tmp/b_2mb.pdf")],
            summary="2 PDFs comprimidos",
            items=[
                FileResult(
                    Path("/tmp/a.pdf"),
                    Path("/tmp/a_2mb.pdf"),
                    True,
                    "1.23 MB → 0.45 MB",
                ),
                FileResult(
                    Path("/tmp/b.pdf"),
                    Path("/tmp/b_2mb.pdf"),
                    True,
                    "2.10 MB → 1.80 MB (no se alcanzó el objetivo)",
                ),
            ],
        )
    )

    assert tool._row_paths == [Path("/tmp/a_2mb.pdf"), Path("/tmp/b_2mb.pdf")]


class _ThumbStub(MultiFileToolPanel):
    meta = ToolMeta(id="thumb-stub", category="c")
    show_thumbnails = True

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


def test_no_thumbnails_by_default(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current, **kw: launched.append(paths),
    )
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool._thumb_boxes == {}
    assert launched == []


def test_thumbnails_flag_creates_placeholders_and_loads(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current, **kw: launched.append(list(paths)),
    )
    tool = _build(_ThumbStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.png"]))

    assert set(tool._thumb_boxes) == {"/tmp/a.pdf", "/tmp/b.png"}
    assert launched[-1] == [Path("/tmp/a.pdf"), Path("/tmp/b.png")]


def test_thumb_ready_swaps_placeholder_for_image(monkeypatch):
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current, **kw: None,
    )
    tool = _build(_ThumbStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    box = tool._thumb_boxes["/tmp/a.pdf"]
    assert isinstance(box.content, ft.Icon)  # placeholder

    tool._on_thumb_ready(Path("/tmp/a.pdf"), b"png-falso")

    assert isinstance(box.content, ft.Image)


def test_thumb_ready_none_keeps_icon_and_gone_row_is_noop(monkeypatch):
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current, **kw: None,
    )
    tool = _build(_ThumbStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    box = tool._thumb_boxes["/tmp/a.pdf"]

    tool._on_thumb_ready(Path("/tmp/a.pdf"), None)  # no renderizable
    assert isinstance(box.content, ft.Icon)  # el icono se queda

    tool._on_thumb_ready(Path("/tmp/zzz.pdf"), b"x")  # fila inexistente: no lanza


# ── Estado del resultado: éxito, parcial y error se distinguen ──────────────


def _done(tool, result):
    calls = {}
    handle = JobHandle()

    def fake_run_job(**kwargs):
        calls.update(kwargs)
        return handle

    tool.build_panel(ToolContext(page=_FakePage(), run_job=fake_run_job))
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
    tool.run_btn.on_click(None)
    calls["on_done"](result)
    return tool


class _RunnableMulti(MultiFileToolPanel):
    meta = ToolMeta(id="multi-run", category="c")

    def make_params(self):
        return BaseParams()

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


def test_success_status_shows_check_icon():
    tool = _done(
        _RunnableMulti(), ToolResult(outputs=[Path("/tmp/x.pdf")], summary="Listo")
    )
    assert tool._status_icon.visible is True
    assert tool._status_icon.name == ft.Icons.CHECK_CIRCLE
    assert tool.status.color is None


def test_partial_batch_status_shows_warning_icon():
    tool = _done(
        _RunnableMulti(),
        ToolResult(
            outputs=[Path("/tmp/a_x.pdf")],
            summary="1 de 2 PDFs procesados",
            items=[
                FileResult(Path("/tmp/a.pdf"), Path("/tmp/a_x.pdf"), True, "→ a_x.pdf"),
                FileResult(Path("/tmp/b.pdf"), None, False, "Contraseña incorrecta."),
            ],
        ),
    )
    assert tool._status_icon.name == ft.Icons.WARNING_AMBER_ROUNDED
    assert tool._status_icon.color == ft.Colors.ERROR


def test_failed_row_message_uses_error_color():
    tool = _done(
        _RunnableMulti(),
        ToolResult(
            outputs=[Path("/tmp/a_x.pdf")],
            summary="1 de 2 PDFs procesados",
            items=[
                FileResult(Path("/tmp/a.pdf"), Path("/tmp/a_x.pdf"), True, "→ a_x.pdf"),
                FileResult(Path("/tmp/b.pdf"), None, False, "Contraseña incorrecta."),
            ],
        ),
    )

    def message_text(row):
        return next(
            c
            for c in row.controls
            if isinstance(c, ft.Text)
            and c.value in {"→ a_x.pdf", "Contraseña incorrecta."}
        )

    ok_row, bad_row = tool._file_list.controls
    assert message_text(bad_row).color == ft.Colors.ERROR
    assert message_text(ok_row).color != ft.Colors.ERROR


def test_error_status_shows_error_icon_and_color():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    assert tool._status_icon.visible is True
    assert tool._status_icon.name == ft.Icons.ERROR_OUTLINE
    assert tool.status.color == ft.Colors.ERROR


def test_invalid_params_is_shown_as_error():
    from pdftool.ui.panel_base import InvalidParams

    class _Invalid(_RunnableStub):
        def make_params(self):
            raise InvalidParams("Escribe una contraseña.")

    tool = _build(_Invalid())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool.run_btn.on_click(None)
    assert tool.status.value == "Escribe una contraseña."
    assert tool._status_icon.name == ft.Icons.ERROR_OUTLINE


def test_new_pick_clears_error_styling():
    tool = _build(_SingleStub())
    tool._on_error(RuntimeError("boom"))
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool._status_icon.visible is False
    assert tool.status.color is None


# ── Dividir: un PDF que no se puede leer no deja el panel incoherente ───────


def test_after_pick_failure_resets_selection_and_shows_error(tmp_path):
    from pdftool.tools.split.panel import SplitTool

    good = tmp_path / "bueno.pdf"
    with pymupdf.open() as d:
        for _ in range(3):
            d.new_page()
        d.save(str(good))
    broken = tmp_path / "roto.pdf"
    broken.write_bytes(b"no soy un pdf" * 50)

    tool = SplitTool()
    tool.build_panel(ToolContext(page=_FakePage(), run_job=_sync_run_job))
    tool._on_pick(_FakeEvent([str(good)]))
    assert tool._pages == 3

    tool._on_pick(_FakeEvent([str(broken)]))

    assert tool.can_run() is False
    assert tool.run_btn.disabled is True
    assert tool._pages == 0
    assert tool._status_icon.name == ft.Icons.ERROR_OUTLINE
    assert "dañado" in tool.status.value


def test_split_every_field_has_no_redundant_label():
    from pdftool.tools.split.panel import SplitTool

    tool = _build(SplitTool())
    assert tool._every_field.label is None


# ── Comprimir: coma decimal ─────────────────────────────────────────────────


def test_compress_accepts_decimal_comma():
    from pdftool.tools.compress.panel import CompressTool

    tool = _build(CompressTool())
    tool._target_field.value = "2,5"
    assert tool.make_params().target_mb == 2.5


def test_compress_invalid_target_explains_what_to_write():
    from pdftool.tools.compress.panel import CompressTool
    from pdftool.ui.panel_base import InvalidParams

    tool = _build(CompressTool())
    tool._target_field.value = "abc"
    with pytest.raises(InvalidParams, match="2,5"):
        tool.make_params()


# ── Proteger: confirmación y acción explícita ───────────────────────────────


def _protect():
    from pdftool.tools.protect.panel import ProtectTool

    return _build(ProtectTool())


def test_protect_requires_matching_confirmation():
    from pdftool.ui.panel_base import InvalidParams

    tool = _protect()
    tool._pw_field.value = "secreta"
    tool._confirm_field.value = "secretx"
    with pytest.raises(InvalidParams, match="no coinciden"):
        tool.make_params()
    tool._confirm_field.value = "secreta"
    assert tool.make_params().password == "secreta"


def test_protect_cta_and_labels_follow_the_mode():
    tool = _protect()
    assert tool.run_btn.text == "Proteger"
    assert tool._confirm_field.visible is True

    tool._mode_dd.value = "remove"
    tool._mode_dd.on_change(None)

    assert tool.run_btn.text == "Quitar contraseña"
    assert tool.run_btn.icon == ft.Icons.LOCK_OPEN
    assert tool._pw_field.label == "Contraseña actual"
    assert tool._confirm_field.visible is False


def test_remove_mode_does_not_need_confirmation():
    tool = _protect()
    tool._mode_dd.value = "remove"
    tool._mode_dd.on_change(None)
    tool._pw_field.value = "clave"
    tool._confirm_field.value = ""
    assert tool.make_params().password == "clave"


def test_split_reads_the_page_count_in_the_background(tmp_path):
    from pdftool.tools.split.panel import SplitTool

    pdf = tmp_path / "doc.pdf"
    with pymupdf.open() as d:
        for _ in range(4):
            d.new_page()
        d.save(str(pdf))
    calls = {}

    def deferred_run_job(**kwargs):
        calls.update(kwargs)
        return JobHandle()

    tool = SplitTool()
    tool.build_panel(ToolContext(page=_FakePage(), run_job=deferred_run_job))
    tool._on_pick(_FakeEvent([str(pdf)]))

    assert "work" in calls  # no se abrió el PDF en el hilo de la UI
    assert tool.can_run() is False
    assert "leyendo" in tool._file_label.value

    calls["on_done"](calls["work"](lambda p, m: None))

    assert tool._pages == 4
    assert tool._file_label.value == "doc.pdf · 4 páginas"
    assert tool.can_run() is True
    assert tool.run_btn.disabled is False


# ── Pulido de la Fase 2 ──────────────────────────────────────────────────────


def _row_texts(row):
    return [c for c in row.controls if isinstance(c, ft.Text)]


def test_guidance_and_row_results_use_readable_sizes():
    tool = _build(_MultiStub())
    assert tool._empty_hint.size >= 14
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool._results = ["→ a_x.pdf"]
    tool._refresh()
    result_text = next(
        t for t in _row_texts(tool._file_list.controls[0]) if t.value == "→ a_x.pdf"
    )
    assert result_text.size >= 14


def _tooltips(row):
    return [getattr(c, "tooltip", None) or "" for c in row.controls]


def test_only_merge_offers_reordering():
    from pdftool.tools.compress.panel import CompressTool
    from pdftool.tools.images2pdf.panel import ImagesToPdfTool
    from pdftool.tools.merge.panel import MergeTool

    for tool_cls, reorderable in (
        (MergeTool, True),
        (CompressTool, False),
        (ImagesToPdfTool, False),
    ):
        tool = _build(tool_cls())
        tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
        tips = " ".join(_tooltips(tool._file_list.controls[0]))
        assert ("Bajar" in tips) is reorderable, tool_cls.__name__


def test_images_to_pdf_explains_one_pdf_per_image():
    from pdftool.tools.images2pdf.panel import ImagesToPdfTool

    meta = ImagesToPdfTool.meta
    assert meta.description == "Crea un PDF por cada imagen (JPG o PNG)."
    assert ImagesToPdfTool.icon == ft.Icons.PHOTO_LIBRARY


def test_watermark_labels_name_units_and_action():
    from pdftool.tools.watermark.panel import WatermarkTool

    tool = _build(WatermarkTool())
    assert tool._size_field.label == "Tamaño del texto (pt)"
    assert tool.run_btn.text == "Añadir marca de agua"


def test_clearing_the_list_can_be_undone():
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))

    tool._clear_all(None)

    assert tool.collect_inputs() == []
    snack = tool._page.opened[-1]
    assert isinstance(snack, ft.SnackBar)
    assert snack.action == "Deshacer"
    snack.on_action(None)
    assert tool.collect_inputs() == [Path("/tmp/a.pdf"), Path("/tmp/b.pdf")]


def test_saving_the_diagnostic_report_is_confirmed(tmp_path, monkeypatch):
    import pdftool.ui.logs as logs_mod

    monkeypatch.setattr(logs_mod, "log_paths", lambda: [])
    tool = _build(_SingleStub())
    assert tool._log_btn.text == "Guardar informe de diagnóstico"

    class _Saved:
        path = str(tmp_path / "informe.txt")

    tool._log_picker.on_result(_Saved())

    snack = tool._page.opened[-1]
    assert isinstance(snack, ft.SnackBar)
    assert "informe.txt" in snack.content.value


def test_invalid_field_is_marked_and_cleared_on_the_next_run():
    from pdftool.tools.compress.panel import CompressTool

    calls = {}
    tool = CompressTool()
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool._target_field.value = "abc"

    tool.run_btn.on_click(None)

    assert tool._target_field.error_text == tool.status.value
    assert "2,5" in tool._target_field.error_text

    tool._target_field.value = "3"
    tool.run_btn.on_click(None)
    assert not tool._target_field.error_text
    assert "work" in calls


def test_returning_to_a_panel_refreshes_output_dir_dependents():
    tool = _build(_MultiStub())
    calls = []
    tool.on_output_dir_changed = lambda: calls.append(1)
    tool.build_panel(tool._ctx)
    assert calls == [1]


def test_invalid_params_is_a_user_error():
    from pdftool.core.errors import UserError
    from pdftool.ui.panel_base import InvalidParams

    assert issubclass(InvalidParams, UserError)


def test_user_error_from_make_params_is_shown_as_validation_error():
    from pdftool.core.errors import UserError

    class _Bad(_RunnableStub):
        def make_params(self):
            raise UserError("Nombre de salida inválido.")

    calls = {}
    tool = _Bad()
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool.run_btn.on_click(None)

    assert tool.status.value == "Nombre de salida inválido."
    assert tool._status_icon.name == ft.Icons.ERROR_OUTLINE
    assert calls == {}


def test_run_logic_defaults_to_the_declared_logic():
    seen = {}

    def fake_logic(inputs, params, progress):
        seen.update(inputs=inputs, params=params)
        return ToolResult(outputs=[], summary="ok")

    class _Declared(SingleFileToolPanel):
        meta = ToolMeta(id="declared", category="c")
        logic = staticmethod(fake_logic)

        def make_params(self):
            return BaseParams()

    params = BaseParams()
    result = _Declared().run_logic([Path("/tmp/a.pdf")], params, lambda p, m: None)
    assert result.summary == "ok"
    assert seen == {"inputs": [Path("/tmp/a.pdf")], "params": params}


@pytest.mark.parametrize("tool", _tools(), ids=lambda t: t.meta.id)
def test_real_tools_declare_their_logic(tool):
    assert "run_logic" not in type(tool).__dict__
    assert type(tool).spec is not None
    assert type(tool).logic is type(tool).spec.run


# ── Entradas bloqueadas mientras corre un trabajo ────────────────────────────


def _row_buttons(tool):
    return [
        c
        for row in tool._file_list.controls
        for c in row.controls
        if isinstance(c, ft.IconButton) and "Quitar" in (c.tooltip or "")
    ]


def test_inputs_are_locked_while_a_job_runs():
    tool = _RunnableMulti()
    calls = {}
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    assert tool._pick_btn.disabled is False

    tool.run_btn.on_click(None)

    assert tool._pick_btn.disabled is True
    assert tool._clear_btn.disabled is True
    assert all(b.disabled for b in _row_buttons(tool))

    calls["on_done"](ToolResult(outputs=[], summary="Listo"))

    assert tool._pick_btn.disabled is False
    assert tool._clear_btn.disabled is False
    assert not any(b.disabled for b in _row_buttons(tool))


def test_cancel_and_error_unlock_the_inputs():
    for finish in ("cancel", "error"):
        tool = _RunnableStub()
        _ctx, calls, _handle = _running(tool)
        assert tool._pick_btn.disabled is True
        if finish == "cancel":
            tool.cancel_btn.on_click(None)
        else:
            calls["on_error"](RuntimeError("boom"))
        assert tool._pick_btn.disabled is False, finish


def test_protect_clears_passwords_after_a_successful_run():
    from pdftool.tools.protect.panel import ProtectTool

    calls = {}
    tool = ProtectTool()
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool._pw_field.value = tool._confirm_field.value = "secreta"
    tool.run_btn.on_click(None)

    calls["on_done"](ToolResult(outputs=[Path("/tmp/a_protegido.pdf")], summary="ok"))

    assert tool._pw_field.value == ""
    assert tool._confirm_field.value == ""


def test_result_warnings_are_shown_below_the_summary():
    tool = _done(
        _RunnableMulti(),
        ToolResult(
            outputs=[Path("/tmp/x.pdf")],
            summary="Listo",
            warnings=["Algunas páginas se convirtieron en imagen."],
        ),
    )
    assert tool._warnings.visible is True
    assert "convirtieron en imagen" in tool._warnings.value
    assert tool._warnings in tool._feedback.controls

    tool._on_pick(_FakeEvent(["/tmp/c.pdf"]))
    assert tool._warnings.visible is False


def test_rows_with_warnings_show_an_explained_icon():
    tool = _done(
        _RunnableMulti(),
        ToolResult(
            outputs=[Path("/tmp/a_x.pdf"), Path("/tmp/b_x.pdf")],
            summary="2 archivos",
            items=[
                FileResult(
                    Path("/tmp/a.pdf"),
                    Path("/tmp/a_x.pdf"),
                    True,
                    "→ a_x.pdf",
                    warnings=("Se convirtieron en imagen.",),
                ),
                FileResult(Path("/tmp/b.pdf"), Path("/tmp/b_x.pdf"), True, "→ b_x.pdf"),
            ],
        ),
    )

    def warning_icons(row):
        return [
            c
            for c in row.controls
            if isinstance(c, ft.Icon) and c.name == ft.Icons.WARNING_AMBER_ROUNDED
        ]

    first, second = tool._file_list.controls
    (icon,) = warning_icons(first)
    assert icon.tooltip == "Se convirtieron en imagen."
    assert icon.semantics_label == "Aviso: Se convirtieron en imagen."
    assert warning_icons(second) == []


def test_file_list_is_a_lazy_list_view():
    tool = _build(_MultiStub())
    assert isinstance(tool._file_list, ft.ListView)
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.pdf"]))
    assert tool._file_list.expand is True


def test_adding_many_files_deduplicates_quickly():
    import time

    tool = _build(_MultiStub())
    paths = [f"/tmp/doc_{i}.pdf" for i in range(3000)]
    tool._refresh = lambda: None  # mide solo la deduplicación
    started = time.monotonic()
    tool._on_pick(_FakeEvent(paths + paths))
    elapsed = time.monotonic() - started
    assert len(tool.collect_inputs()) == 3000
    assert elapsed < 0.2


# ── Atajos de teclado ────────────────────────────────────────────────────────


class _Key:
    def __init__(self, key, ctrl=False, meta=False):
        self.key, self.ctrl, self.meta = key, ctrl, meta
        self.shift = self.alt = False


def test_shortcuts_open_the_picker_and_run():
    from pdftool.ui.app import _handle_shortcut

    tool = _RunnableStub()
    calls = {}
    tool.build_panel(
        ToolContext(page=_FakePage(), run_job=lambda **kw: calls.update(kw))
    )
    picked = []
    tool._picker.pick_files = lambda **kw: picked.append(kw)

    assert _handle_shortcut(_Key("O", ctrl=True), tool) is True
    assert len(picked) == 1

    assert _handle_shortcut(_Key("Enter", meta=True), tool) is True
    assert calls == {}  # sin archivo, Ejecutar está deshabilitado: no hace nada

    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    _handle_shortcut(_Key("Enter", ctrl=True), tool)
    assert "work" in calls


def test_shortcuts_need_a_modifier_and_a_tool():
    from pdftool.ui.app import _handle_shortcut

    tool = _build(_RunnableStub())
    picked = []
    tool._picker.pick_files = lambda **kw: picked.append(kw)

    assert _handle_shortcut(_Key("O"), tool) is False
    assert _handle_shortcut(_Key("O", ctrl=True), None) is False
    assert picked == []


def test_open_shortcut_is_ignored_while_running():
    tool = _RunnableStub()
    _running(tool)
    picked = []
    tool._picker.pick_files = lambda **kw: picked.append(kw)
    tool.shortcut_open()
    assert picked == []


def test_buttons_advertise_their_shortcuts():
    from pdftool.ui.platform import shortcut_label

    tool = _build(_RunnableStub())
    assert shortcut_label("O") in tool._pick_btn.tooltip
    assert shortcut_label("Enter") in tool.run_btn.tooltip


def test_compress_options_wrap_instead_of_overflowing():
    """A la anchura mínima, objetivo + modo + ayuda no caben en una fila."""
    from pdftool.tools.compress.panel import CompressTool

    tool = _build(CompressTool())
    row = next(
        c
        for c in tool.extra_controls()
        if isinstance(c, ft.Row) and any(x is tool._mode_dd for x in c.controls)
    )
    assert row.wrap is True


def test_compress_options_are_top_aligned():
    """El texto de ayuda del objetivo alarga su campo: centrados en vertical,
    el campo y el desplegable quedaban a alturas distintas."""
    from pdftool.tools.compress.panel import CompressTool

    tool = _build(CompressTool())
    row = next(
        c
        for c in tool.extra_controls()
        if isinstance(c, ft.Row) and any(x is tool._mode_dd for x in c.controls)
    )
    assert row.vertical_alignment == ft.CrossAxisAlignment.START
