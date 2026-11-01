from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, Literal

from platformdirs import user_data_dir
from pydantic import BaseModel, Field, ValidationError

from pdftool.core.atomic import atomic_write_text

APP_NAME = "pdf-tool"
APP_AUTHOR = "juanmaAV"


def data_dir() -> Path:
    d = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_path() -> Path:
    return data_dir() / "settings.json"


ThemeSetting = Literal["system", "light", "dark"]

# Versión del formato de settings.json. Subirla cuando un cambio necesite
# migrar datos guardados; los archivos sin versión son la versión 1.
SCHEMA_VERSION = 1


class Settings(BaseModel):
    schema_version: int = SCHEMA_VERSION
    theme_mode: ThemeSetting = "system"
    # "system" o un código de idioma con diccionario (`pdftool/i18n/locales`).
    language: str = "system"
    # Carpeta de salida global; None → junto al original. Se guarda como texto
    # porque el JSON no tiene tipo ruta.
    output_dir: str | None = None
    # Preferencias propias de cada herramienta, por `meta.id`.
    tools: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def tool(self, tool_id: str) -> dict[str, Any]:
        """Preferencias de una herramienta (se crean vacías al pedirlas)."""
        return self.tools.setdefault(tool_id, {})


def _recover(raw: dict[str, Any]) -> Settings:
    """Conserva cada campo válido y deja en su default solo los inválidos."""
    defaults = Settings()
    kept: dict[str, Any] = {}
    for name in Settings.model_fields:
        if name not in raw:
            continue
        try:
            Settings.model_validate({name: raw[name]})
        except ValidationError:
            continue
        kept[name] = raw[name]
    return Settings.model_validate({**defaults.model_dump(), **kept})


def load_settings(path: Path | None = None) -> Settings:
    path = path or settings_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return Settings()
    try:
        raw = json.loads(text)
        if not isinstance(raw, dict):
            raise ValueError("settings.json no es un objeto")
    except ValueError:
        # Ilegible: se guarda una copia antes de que el próximo guardado lo
        # sustituya, y la app arranca con los valores por defecto.
        with contextlib.suppress(OSError):
            atomic_write_text(path.with_name(path.name + ".bak"), text)
        return Settings()
    try:
        return Settings.model_validate(raw)
    except ValidationError:
        # Un campo inválido no debe llevarse por delante el resto.
        return _recover(raw)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, settings.model_dump_json(indent=2))
