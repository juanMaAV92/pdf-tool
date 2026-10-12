import flet as ft

from pdftool.ui.app import _build_update_banner


class _Page:
    def __init__(self):
        self.launched = []
        self.updates = 0

    def launch_url(self, url):
        self.launched.append(url)

    def update(self):
        self.updates += 1


URL = "https://github.com/x/y/releases/tag/v9.9.9"


def test_banner_starts_hidden_and_shows_inside_the_layout():
    """Barra en el layout, no un overlay: abierto con page.open, el ft.Banner
    se dibujaba encima, oscurecido, ilegible en tema claro y tapando el título."""
    page = _Page()
    banner = _build_update_banner(page)
    assert isinstance(banner, ft.Container)
    assert banner.visible is False
    banner.show(URL)
    assert banner.visible is True
    assert page.updates == 1


def test_banner_uses_high_contrast_theme_pairs():
    banner = _build_update_banner(_Page())
    assert banner.bgcolor == ft.Colors.PRIMARY_CONTAINER
    assert banner.text.color == ft.Colors.ON_PRIMARY_CONTAINER
    assert banner.dismiss_button.style.color == ft.Colors.ON_PRIMARY_CONTAINER
    assert isinstance(banner.download_button, ft.FilledButton)


def test_banner_can_be_dismissed():
    banner = _build_update_banner(_Page())
    banner.show(URL)
    assert [banner.download_button.text, banner.dismiss_button.text] == [
        "Descargar",
        "Ahora no",
    ]
    banner.dismiss_button.on_click(None)
    assert banner.visible is False


def test_download_opens_the_release_and_hides_the_banner():
    page = _Page()
    banner = _build_update_banner(page)
    banner.show(URL)
    banner.download_button.on_click(None)
    assert page.launched == [URL]
    assert banner.visible is False


def test_update_check_runs_outside_the_job_pool():
    import threading

    from pdftool.ui.app import _start_update_check

    found = []
    done = threading.Event()

    def check():
        assert threading.current_thread().name == "pdftool-update-check"
        return "https://github.com/x/y/releases/tag/v9"

    thread = _start_update_check(lambda url: (found.append(url), done.set()), check)
    thread.join(timeout=5)
    assert found == ["https://github.com/x/y/releases/tag/v9"]


def test_update_check_without_new_version_does_not_notify():
    from pdftool.ui.app import _start_update_check

    found = []
    _start_update_check(found.append, lambda: None).join(timeout=5)
    assert found == []
