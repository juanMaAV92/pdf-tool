import logging

import flet as ft

from pdftool import __version__
from pdftool.core.logger import setup_logging
from pdftool.ui.app import build_app


def main() -> None:
    setup_logging()
    logging.getLogger("pdftool").info("app v%s iniciada", __version__)
    ft.app(target=build_app)


if __name__ == "__main__":
    main()
