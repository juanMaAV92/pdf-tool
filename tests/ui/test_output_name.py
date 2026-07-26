from pathlib import Path

import pytest

from pdftool.core.naming import unique_path
from pdftool.core.plugin import ToolContext
from pdftool.tools.merge.panel import MergeTool
from pdftool.ui.panel_base import InvalidParams, OutputNameField, parse_output_name


def test_none_and_empty_and_blank_give_none():
    assert parse_output_name(None) is None
    assert parse_output_name("") is None
    assert parse_output_name("   ") is None


def test_strips_surrounding_spaces():
    assert parse_output_name("  informe  ") == "informe"


def test_drops_pdf_extension_case_insensitive():
    assert parse_output_name("informe.pdf") == "informe"
    assert parse_output_name("Informe.PDF") == "Informe"


def test_only_extension_gives_none():
    assert parse_output_name(".pdf") is None


@pytest.mark.parametrize("bad", ["a/b", "a\\b", "a:b", "a\x00b",
                                 "a?b", "a|b", "a<b", "a>b", "a*b", 'a"b'])
def test_path_characters_raise_invalid_params(bad):
    with pytest.raises(InvalidParams):
        parse_output_name(bad)


def test_field_has_hint_and_bounded_width():
    field = OutputNameField(resolve=lambda _base: None)
    assert field.hint_text == "Nombre de salida (opcional)"
    assert field.width == 280


class _FakePage:
    def __init__(self) -> None:
        self.overlay = []

    def update(self) -> None:
        pass


def _build(tool):
    tool.build_panel(ToolContext(page=_FakePage(), run_job=lambda **kwargs: None))
    return tool


def test_merge_panel_passes_sanitized_name():
    tool = _build(MergeTool())
    tool._name_field.value = "  informe.pdf "
    assert tool.make_params().output_name == "informe"


def test_merge_panel_empty_name_gives_default():
    tool = _build(MergeTool())
    assert tool.make_params().output_name is None


def test_merge_panel_invalid_name_raises():
    tool = _build(MergeTool())
    tool._name_field.value = "a/b"
    with pytest.raises(InvalidParams):
        tool.make_params()


@pytest.mark.parametrize("reserved", ["con", "CON", "Con.pdf", "PRN", "AUX", "NUL"]
                         + [f"COM{i}" for i in range(1, 10)]
                         + [f"LPT{i}" for i in range(1, 10)])
def test_windows_reserved_names_raise_invalid_params(reserved):
    with pytest.raises(InvalidParams, match="reservado por Windows"):
        parse_output_name(reserved)


@pytest.mark.parametrize("ok", ["CONFIDENCIAL", "consejo", "com10", "lpt0", "aux2"])
def test_names_that_merely_start_with_reserved_pass(ok):
    assert parse_output_name(ok) == ok


def _field_over(tmp_path, existing=(), files=(Path("x.pdf"),)):
    """Campo cuyo `resolve` imita a output_path_for_merge sobre tmp_path."""
    for name in existing:
        (tmp_path / name).write_bytes(b"x")

    def resolve(base):
        if not files or base is None:
            return None
        return unique_path(tmp_path / f"{base}.pdf")

    return OutputNameField(resolve=resolve)


def test_helper_empty_when_no_name(tmp_path):
    field = _field_over(tmp_path)
    field.value = ""
    field.refresh()
    assert not field.helper_text


def test_helper_empty_when_no_files(tmp_path):
    field = _field_over(tmp_path, files=())
    field.value = "2022"
    field.refresh()
    assert not field.helper_text


def test_helper_shows_final_name_when_free(tmp_path):
    field = _field_over(tmp_path)
    field.value = "2022"
    field.refresh()
    assert field.helper_text == "Se guardará como «2022.pdf»"


def test_helper_warns_when_name_is_taken(tmp_path):
    field = _field_over(tmp_path, existing=["2022.pdf"])
    field.value = "2022"
    field.refresh()
    assert field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"


def test_helper_empty_when_name_is_invalid(tmp_path):
    field = _field_over(tmp_path)
    field.value = "a/b"
    field.refresh()
    assert not field.helper_text


def test_helper_clears_after_warning_when_files_are_removed(tmp_path):
    """Verifica la transición aviso -> vacío: el helper_text de Flet 0.28.2
    coacciona None a '' en el setter, así que `is None` no detecta este caso
    (ver reporte de hallazgos)."""
    files: list[Path] = [Path("x.pdf")]
    (tmp_path / "2022.pdf").write_bytes(b"x")

    def resolve(base):
        if not files or base is None:
            return None
        return unique_path(tmp_path / f"{base}.pdf")

    field = OutputNameField(resolve=resolve)
    field.value = "2022"
    field.refresh()
    assert field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"

    files.clear()
    field.refresh()
    assert not field.helper_text


def test_warning_and_normal_helpers_use_different_colors(tmp_path):
    free = _field_over(tmp_path)
    free.value = "libre"
    free.refresh()
    taken = _field_over(tmp_path, existing=["ocupado.pdf"])
    taken.value = "ocupado"
    taken.refresh()
    assert free.helper_style.color != taken.helper_style.color


def test_merge_panel_helper_warns_about_existing_output(tmp_path):
    (tmp_path / "2022.pdf").write_bytes(b"previo")
    entrada = tmp_path / "a.pdf"
    entrada.write_bytes(b"x")

    tool = _build(MergeTool())
    tool._files = [entrada]
    tool._name_field.value = "2022"
    tool._name_field.refresh()

    assert tool._name_field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"


def test_merge_panel_helper_is_empty_without_files():
    tool = _build(MergeTool())
    tool._name_field.value = "2022"
    tool._name_field.refresh()
    assert not tool._name_field.helper_text


def test_merge_panel_refresh_updates_helper_from_file_list(tmp_path):
    """El wiring real: `_refresh()` (cambio de lista de archivos) debe llegar
    al helper del campo de nombre vía `on_inputs_changed`, no solo
    `field.refresh()` llamado a mano."""
    (tmp_path / "2022.pdf").write_bytes(b"previo")
    entrada = tmp_path / "a.pdf"
    entrada.write_bytes(b"x")

    tool = _build(MergeTool())
    tool._files = [entrada]
    tool._name_field.value = "2022"
    tool._refresh()

    assert tool._name_field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"


from pdftool.core.config import Settings


def test_merge_panel_predicts_over_the_chosen_folder(tmp_path):
    """Con destino fijo, el aviso mira la carpeta destino, no la del original."""
    destino = tmp_path / "destino"
    destino.mkdir()
    (destino / "2022.pdf").write_bytes(b"previo")
    entrada = tmp_path / "a.pdf"
    entrada.write_bytes(b"x")

    tool = _build(MergeTool())
    tool._out_dir.settings_path = tmp_path / "settings.json"
    tool._out_dir.set_dir(destino)
    tool._files = [entrada]
    tool._name_field.value = "2022"
    tool._name_field.refresh()

    assert tool._name_field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"
    tool._out_dir.set_dir(None)


def test_merge_panel_helper_is_clean_when_only_the_origin_is_taken(tmp_path):
    """El mismo nombre ocupado en la carpeta del original no debe avisar."""
    destino = tmp_path / "destino"
    destino.mkdir()
    (tmp_path / "2022.pdf").write_bytes(b"previo")
    entrada = tmp_path / "a.pdf"
    entrada.write_bytes(b"x")

    tool = _build(MergeTool())
    tool._out_dir.settings_path = tmp_path / "settings.json"
    tool._out_dir.set_dir(destino)
    tool._files = [entrada]
    tool._name_field.value = "2022"
    tool._name_field.refresh()

    assert tool._name_field.helper_text == "Se guardará como «2022.pdf»"
    tool._out_dir.set_dir(None)


def test_changing_the_destination_refreshes_the_helper(tmp_path):
    """El callback on_change del widget re-predice sin tocar el campo."""
    destino = tmp_path / "destino"
    destino.mkdir()
    (destino / "2022.pdf").write_bytes(b"previo")
    entrada = tmp_path / "a.pdf"
    entrada.write_bytes(b"x")

    tool = _build(MergeTool())
    tool._out_dir.settings_path = tmp_path / "settings.json"
    tool._files = [entrada]
    tool._name_field.value = "2022"
    tool._name_field.refresh()
    assert tool._name_field.helper_text == "Se guardará como «2022.pdf»"

    tool._out_dir.set_dir(destino)

    assert tool._name_field.helper_text == "Ya existe — se guardará como «2022 (1).pdf»"
    tool._out_dir.set_dir(None)


def test_rebuilding_a_panel_does_not_leak_pickers_in_the_overlay():
    """Navegar a una herramienta y volver no debe acumular FilePickers."""
    page = _FakePage()
    ctx = ToolContext(page=page, run_job=lambda **kwargs: None)
    tool = MergeTool()

    tool.build_panel(ctx)
    primero = tool._out_dir
    tras_el_primero = len(page.overlay)

    tool.build_panel(ctx)

    assert tool._out_dir is primero
    assert len(page.overlay) == tras_el_primero
