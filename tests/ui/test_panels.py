import logging
from pathlib import Path

import fitz
import flet as ft
import pytest

from pdftool.core import registry
from pdftool.core.errors import GENERIC_MESSAGE, UserError
from pdftool.core.jobs import JobHandle
from pdftool.core.plugin import (
    BaseParams,
    FileResult,
    ToolContext,
    ToolMeta,
    ToolResult,
)
from pdftool.ui.file_list import MultiFileToolPanel
from pdftool.ui.panel_base import SingleFileToolPanel


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


class _RunnableStub(SingleFileToolPanel):
    meta = ToolMeta(
        id="runnable-stub", name="R", description="d", icon="", category="c"
    )

    def make_params(self):
        return BaseParams()

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


def test_rebuilding_panel_cancels_job_and_ignores_old_callbacks():
    calls = {}
    handle = JobHandle()

    def fake_run_job(**kwargs):
        calls.update(kwargs)
        return handle

    page = _FakePage()
    ctx = ToolContext(page=page, run_job=fake_run_job)
    tool = _RunnableStub()
    tool.build_panel(ctx)
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    tool.run_btn.on_click(None)

    old_progress = calls["on_progress"]
    old_done = calls["on_done"]
    assert handle.cancelled is False

    tool.build_panel(ctx)
    old_progress(1.0, "resultado antiguo")
    old_done(ToolResult(outputs=[Path("/tmp/old.pdf")], summary="antiguo"))

    assert handle.cancelled is True
    assert tool.status.value == ""
    assert tool.open_btn.visible is False


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
    assert tool._feedback.controls[:3] == [
        tool.progress,
        tool._status_row,
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


def test_watermark_opacity_label_shows_decimals():
    # Regresión: con round=0 (default de Flet) el label "{value}" muestra
    # 0 en todo el rango 0.05–0.6 (y 1 en el tope).
    from pdftool.tools.watermark.panel import WatermarkTool

    tool = _build(WatermarkTool())
    assert tool._opacity.round == 2


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
    meta = ToolMeta(id="thumb-stub", name="T", description="d", icon="", category="c")
    show_thumbnails = True

    def make_params(self):
        return None

    def run_logic(self, inputs, params, progress):
        return ToolResult(outputs=[], summary="")


def test_no_thumbnails_by_default(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current: launched.append(paths),
    )
    tool = _build(_MultiStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))

    assert tool._thumb_boxes == {}
    assert launched == []


def test_thumbnails_flag_creates_placeholders_and_loads(monkeypatch):
    launched = []
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async",
        lambda paths, on_ready, is_current: launched.append(list(paths)),
    )
    tool = _build(_ThumbStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf", "/tmp/b.png"]))

    assert set(tool._thumb_boxes) == {"/tmp/a.pdf", "/tmp/b.png"}
    assert launched[-1] == [Path("/tmp/a.pdf"), Path("/tmp/b.png")]


def test_thumb_ready_swaps_placeholder_for_image(monkeypatch):
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async", lambda paths, on_ready, is_current: None
    )
    tool = _build(_ThumbStub())
    tool._on_pick(_FakeEvent(["/tmp/a.pdf"]))
    box = tool._thumb_boxes["/tmp/a.pdf"]
    assert isinstance(box.content, ft.Icon)  # placeholder

    tool._on_thumb_ready(Path("/tmp/a.pdf"), b"png-falso")

    assert isinstance(box.content, ft.Image)


def test_thumb_ready_none_keeps_icon_and_gone_row_is_noop(monkeypatch):
    monkeypatch.setattr(
        "pdftool.ui.file_list.load_async", lambda paths, on_ready, is_current: None
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
    meta = ToolMeta(id="multi-run", name="M", description="d", icon="", category="c")

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
    with fitz.open() as d:
        for _ in range(3):
            d.new_page()
        d.save(str(good))
    broken = tmp_path / "roto.pdf"
    broken.write_bytes(b"no soy un pdf" * 50)

    tool = _build(SplitTool())
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
