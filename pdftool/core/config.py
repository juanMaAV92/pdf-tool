from __future__ import annotations

from pathlib import Path
from typing import Literal

from platformdirs import user_data_dir
from pydantic import BaseModel, ValidationError

from pdftool.core.atomic import atomic_write_text

APP_NAME = "pdf-tool"
APP_AUTHOR = "juanmaAV"


def data_dir() -> Path:
    d = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return data_dir() / "settings.json"


class Settings(BaseModel):
    theme_mode: Literal["system", "light", "dark"] = "system"
    # Carpeta de salida global; None → junto al original. Se guarda como texto
    # porque el JSON no tiene tipo ruta.
    output_dir: str | None = None


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    try:
        return Settings.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError):
        # Unreadable or corrupt settings must not prevent application startup.
        return Settings()


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, settings.model_dump_json(indent=2))
