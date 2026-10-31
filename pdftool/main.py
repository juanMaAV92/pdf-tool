import logging
import sys

from pdftool import __version__
from pdftool.core.logger import setup_logging

GUI_MISSING = (
    "La app de escritorio necesita Flet, que no está instalado.\n"
    "Instálala con:  pipx install 'pdf-tool[gui]'\n"
    "Para la línea de comandos usa:  pdf-tool --help"
)


def main() -> None:
    # Flet es opcional (extra [gui]): `pip install pdf-tool` trae solo la CLI.
    try:
        import flet as ft

        from pdftool.ui.app import build_app
    except ImportError:
        print(GUI_MISSING, file=sys.stderr)
        sys.exit(1)

    setup_logging()
    logging.getLogger("pdftool").info("app v%s iniciada", __version__)
    ft.app(target=build_app)


if __name__ == "__main__":
    main()
