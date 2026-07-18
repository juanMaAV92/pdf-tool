import pytest

from pdftool.ui.panel_base import InvalidParams, output_name_field, parse_output_name


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


@pytest.mark.parametrize("bad", ["a/b", "a\\b", "a:b", "a\x00b"])
def test_path_characters_raise_invalid_params(bad):
    with pytest.raises(InvalidParams):
        parse_output_name(bad)


def test_field_has_hint_and_bounded_width():
    field = output_name_field()
    assert field.hint_text == "Nombre de salida (opcional)"
    assert field.width == 280


from pdftool.core.plugin import ToolContext
from pdftool.tools.merge.panel import MergeTool


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
