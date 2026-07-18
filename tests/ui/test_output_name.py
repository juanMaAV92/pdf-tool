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
