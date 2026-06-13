from __future__ import annotations

import flet as ft

SEED_COLOR = "#4F46E5"  # índigo moderno


def build_theme() -> ft.Theme:
    return ft.Theme(color_scheme_seed=SEED_COLOR)


def resolve_mode(setting: str) -> ft.ThemeMode:
    return {
        "light": ft.ThemeMode.LIGHT,
        "dark": ft.ThemeMode.DARK,
    }.get(setting, ft.ThemeMode.SYSTEM)


def next_mode(setting: str) -> str:
    """Cicla system -> light -> dark -> system para el toggle."""
    return {"system": "light", "light": "dark", "dark": "system"}.get(setting, "light")
