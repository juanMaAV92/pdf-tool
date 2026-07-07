import pytest

from pdftool.core import registry
from pdftool.core.plugin import ToolContext


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
