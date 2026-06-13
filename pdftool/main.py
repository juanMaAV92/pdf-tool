import flet as ft

from pdftool.ui.app import build_app


def main() -> None:
    ft.app(target=build_app)


if __name__ == "__main__":
    main()
