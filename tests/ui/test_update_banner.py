import flet as ft

from pdftool.ui.app import _build_update_banner


class _Page:
    def __init__(self):
        self.closed = []
        self.launched = []

    def close(self, control):
        self.closed.append(control)

    def launch_url(self, url):
        self.launched.append(url)


def test_banner_uses_theme_colors_that_work_in_dark_mode():
    banner = _build_update_banner(_Page())
    assert banner.bgcolor == ft.Colors.SECONDARY_CONTAINER
    assert banner.content.color == ft.Colors.ON_SECONDARY_CONTAINER


def test_banner_can_be_dismissed():
    page = _Page()
    banner = _build_update_banner(page)
    labels = [a.text for a in banner.actions]
    assert labels == ["Descargar", "Ahora no"]
    banner.actions[1].on_click(None)
    assert page.closed == [banner]


def test_download_opens_the_release_and_closes_the_banner():
    page = _Page()
    banner = _build_update_banner(page)
    banner.show("https://github.com/x/y/releases/tag/v9.9.9")
    banner.actions[0].on_click(None)
    assert page.launched == ["https://github.com/x/y/releases/tag/v9.9.9"]
    assert page.closed == [banner]
