from types import SimpleNamespace

import flet as ft

from pdftool.ui.accessibility import HelpButton, NamedIconButton
from pdftool.ui.app import _tool_card


def test_help_can_be_read_on_keyboard_focus_and_hides_on_blur():
    help_button = HelpButton("Ayuda sobre rangos", "Escribe 1-3, 5.")
    assert not help_button.detail.visible
    help_button.on_focus(None)
    assert help_button.detail.visible
    assert help_button.detail.value == "Escribe 1-3, 5."
    help_button.on_blur(None)
    assert not help_button.detail.visible
    help_button.on_click(None)
    assert help_button.detail.visible


def test_home_card_is_standard_button_and_opens_selected_tool():
    opened = []
    tool = SimpleNamespace(
        meta=SimpleNamespace(
            icon=ft.Icons.COMPRESS,
            name="Comprimir PDF",
            description="Reduce el tamaño.",
        )
    )
    card = _tool_card(2, tool, opened.append)
    assert isinstance(card, ft.OutlinedButton)
    card.on_click(None)
    assert opened == [2]


def test_icon_button_exposes_file_specific_name():
    button = NamedIconButton(ft.Icons.CLOSE, "Quitar factura.pdf de la lista")
    assert button.content.semantics_label == "Quitar factura.pdf de la lista"
