from __future__ import annotations

from pathlib import Path

from platformdirs import user_data_dir
from pydantic import BaseModel

APP_NAME = "pdf-tool"
APP_AUTHOR = "juanmaAV"


def data_dir() -> Path:
    d = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return data_dir() / "settings.json"


class Settings(BaseModel):
    theme_mode: str = "system"  # "system" | "light" | "dark"


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    if not path.exists():
        return Settings()
    return Settings.model_validate_json(path.read_text(encoding="utf-8"))


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
