"""Controles estándar con nombres accesibles y ayuda disponible al teclado."""

import flet as ft


def icon_content(icon, label: str) -> ft.Icon:
    return ft.Icon(icon, size=24, semantics_label=label)


class NamedIconButton(ft.IconButton):
    def __init__(self, icon, label: str, **kwargs):
        super().__init__(
            content=icon_content(icon, label),
            tooltip=label,
            focus_color=ft.Colors.PRIMARY_CONTAINER,
            **kwargs,
        )


class HelpButton(NamedIconButton):
    """La ayuda se muestra al foco o al activar el botón, sin un diálogo."""

    def __init__(self, label: str, message: str):
        self.detail = ft.Text(
            message,
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            visible=False,
        )
        super().__init__(ft.Icons.HELP_OUTLINE, label)
        self.tooltip = message
        self.on_focus = self._show
        self.on_click = self._show
        self.on_blur = self._hide

    def _show(self, _e):
        self.detail.visible = True
        if self.page:
            self.page.update()

    def _hide(self, _e):
        self.detail.visible = False
        if self.page:
            self.page.update()
