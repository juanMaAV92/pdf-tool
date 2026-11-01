import logging
import sys

from pdftool import __version__
from pdftool.core.logger import setup_logging
from pdftool.i18n import set_language, system_language, t


def gui_missing() -> str:
    """Aviso cuando falta Flet (extra [gui]), en el idioma del sistema."""
    return t("app.gui_missing")


def main() -> None:
    # Flet es opcional (extra [gui]): `pip install pdf-tool-cli` trae solo la CLI.
    try:
        import flet as ft

        from pdftool.ui.app import build_app
    except ImportError:
        set_language(system_language())
        print(gui_missing(), file=sys.stderr)
        sys.exit(1)

    setup_logging()
    logging.getLogger("pdftool").info("app v%s iniciada", __version__)
    ft.app(target=build_app)


if __name__ == "__main__":
    main()
