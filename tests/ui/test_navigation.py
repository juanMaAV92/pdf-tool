import flet as ft

from pdftool.core.plugin import ToolMeta
from pdftool.ui.app import _build_home, _group_by_category, _Sidebar


class _Tool:
    def __init__(self, id_, name, category):
        self.meta = ToolMeta(
            id=id_, name=name, description="d", icon=ft.Icons.MERGE, category=category
        )


TOOLS = [
    _Tool("merge", "Unir", "Organizar"),
    _Tool("split", "Dividir", "Organizar"),
    _Tool("compress", "Comprimir", "Optimizar"),
    _Tool("protect", "Proteger", "Seguridad"),
]


def test_groups_keep_tool_order_and_first_appearance_of_category():
    groups = _group_by_category(TOOLS)
    assert [(cat, [i for i, _ in items]) for cat, items in groups] == [
        ("Organizar", [0, 1]),
        ("Optimizar", [2]),
        ("Seguridad", [3]),
    ]


def _texts(control):
    found = []

    def walk(c):
        if isinstance(c, ft.Text):
            found.append(c.value)
        for attr in ("controls", "content"):
            child = getattr(c, attr, None)
            if isinstance(child, list):
                for x in child:
                    walk(x)
            elif child is not None:
                walk(child)

    walk(control)
    return found


def test_home_is_one_compact_grid_with_the_category_on_each_card():
    """Una fila por categoría dejaba media pantalla vacía y obligaba a hacer
    scroll: todas las tarjetas comparten una cuadrícula que se ajusta."""
    home = _build_home(TOOLS, lambda i: None)
    grids = [c for c in home.controls if isinstance(c, ft.Row) and c.wrap]
    assert len(grids) == 1
    cards = grids[0].controls
    assert len(cards) == len(TOOLS)
    for card, tool in zip(cards, TOOLS, strict=True):
        texts = _texts(card)
        assert tool.meta.name in texts
        assert tool.meta.category in texts


def test_sidebar_scrolls_and_groups_tools():
    sidebar = _Sidebar(TOOLS, on_home=lambda: None, on_tool=lambda i: None)
    assert isinstance(sidebar.list, ft.ListView)
    texts = _texts(sidebar)
    assert texts[:2] == ["Inicio", "Organizar"]
    assert texts.index("Seguridad") < texts.index("Proteger")


def test_sidebar_items_open_tools_and_mark_the_selection():
    opened, homes = [], []
    sidebar = _Sidebar(TOOLS, on_home=lambda: homes.append(1), on_tool=opened.append)

    sidebar.tool_buttons[2].on_click(None)
    sidebar.home_button.on_click(None)

    assert opened == [2]
    assert homes == [1]

    sidebar.select(2)
    assert sidebar.tool_buttons[2].style.bgcolor == ft.Colors.SECONDARY_CONTAINER
    assert sidebar.tool_buttons[0].style.bgcolor is None
    assert sidebar.home_button.style.bgcolor is None
    sidebar.select(None)
    assert sidebar.home_button.style.bgcolor == ft.Colors.SECONDARY_CONTAINER


def test_sidebar_buttons_have_accessible_names():
    sidebar = _Sidebar(TOOLS, on_home=lambda: None, on_tool=lambda i: None)
    assert sidebar.tool_buttons[0].tooltip == "Unir"
    assert sidebar.home_button.tooltip == "Inicio"
