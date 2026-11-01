"""Textos visibles en el idioma activo (sin Flet).

Un diccionario JSON por idioma en `locales/<código>.json`: añadir un idioma es
añadir un archivo. El inglés es la referencia: si a un diccionario le falta una
clave, se usa la inglesa. Un solo idioma activo por proceso.
"""

from __future__ import annotations

import json
import locale
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

LOCALES_DIR = Path(__file__).parent / "locales"
FALLBACK = "en"

log = logging.getLogger("pdftool.i18n")

_dir: Path = LOCALES_DIR
_cache: dict[str, dict[str, Any] | None] = {}
_active: str = FALLBACK


def use_locales_dir(path: Path | None) -> None:
    """Cambia la carpeta de diccionarios (tests) y limpia la caché."""
    global _dir
    _dir = LOCALES_DIR if path is None else path
    _cache.clear()


def _load(code: str) -> dict[str, Any] | None:
    """Diccionario de `code` en la carpeta activa (con caché)."""
    if code not in _cache:
        _cache[code] = _read(_dir / f"{code}.json")
    return _cache[code]


def _read(path: Path) -> dict[str, Any] | None:
    """Diccionario de `path`, o None si no existe o está roto."""
    data: dict[str, Any] | None = None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw = None
    except (OSError, ValueError) as exc:
        log.warning("Diccionario %s ignorado: %s", path.name, exc)
        raw = None
    if isinstance(raw, dict):
        meta = raw.get("_meta")
        if isinstance(meta, dict) and isinstance(meta.get("name"), str):
            data = raw
        else:
            log.warning("Diccionario %s ignorado: falta _meta.name", path.name)
    return data


def available_languages(locales_dir: Path | None = None) -> list[tuple[str, str]]:
    """(código, nombre propio) de cada diccionario válido, por código."""
    folder = _dir if locales_dir is None else locales_dir
    found = []
    for path in sorted(folder.glob("*.json")):
        data = _load(path.stem) if folder == _dir else _read(path)
        if data is not None:
            found.append((path.stem, data["_meta"]["name"]))
    return found


def _known(code: str) -> bool:
    return _load(code) is not None


def set_language(code: str) -> None:
    """Activa `code`; sin diccionario, inglés."""
    global _active
    _active = code if _known(code) else FALLBACK


def current_language() -> str:
    return _active


def _ui_language() -> str:
    """Idioma de la interfaz del sistema (no la región), p. ej. «es-CO»."""
    if sys.platform == "darwin":
        out = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout
        # Formato: ( "es-CO", "en-US" )
        for token in out.replace("(", " ").replace(")", " ").split(","):
            token = token.strip().strip('"')
            if token:
                return token
    elif sys.platform == "win32":
        import ctypes

        lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
        return locale.windows_locale.get(lcid, "")
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return value.split(":")[0]
    return ""


def system_language() -> str:
    """Código del idioma de la interfaz si hay diccionario; si no, inglés."""
    try:
        raw = _ui_language()
    except Exception:  # cualquier fallo del detector → inglés
        return FALLBACK
    code = raw.replace("_", "-").split("-")[0].split(".")[0].lower()
    return code if code and _known(code) else FALLBACK


def resolve_language(setting: str) -> str:
    """`"system"` o un idioma sin diccionario → el del sistema."""
    if setting != "system" and _known(setting):
        return setting
    return system_language()


def _template(code: str, key: str, count: object) -> str | None:
    data = _load(code)
    if data is None or key not in data:
        return None
    value = data[key]
    if isinstance(value, dict):
        form = "one" if count == 1 else "other"
        value = value.get(form)
    return value if isinstance(value, str) else None


def t(key: str, **params: object) -> str:
    """Texto de `key` en el idioma activo, con `params` como marcadores.

    Nunca lanza: si falta la clave usa el inglés; si el formato falla, prueba
    con el inglés y, si también falla, devuelve la plantilla sin formatear.
    """
    count = params.get("count")
    own = _template(_active, key, count)
    english = _template(FALLBACK, key, count) if _active != FALLBACK else own
    template = own if own is not None else english
    if template is None:
        log.warning("Falta la clave de traducción %s", key)
        return key
    for candidate in (template, english):
        if candidate is None:
            continue
        try:
            return candidate.format(**params)
        except (KeyError, IndexError, ValueError):
            continue
    return template


def fmt_number(value: float, decimals: int) -> str:
    """Número con el separador decimal del idioma activo."""
    data = _load(_active) or {}
    sep = data.get("_meta", {}).get("decimal_separator", ".")
    return f"{value:.{decimals}f}".replace(".", sep)


def param_help(tool_id: str | None, field: str) -> str:
    """Ayuda de un parámetro en el idioma activo."""
    from pdftool.i18n.keys import param_key

    return t(param_key(tool_id, field))


def choice_label(tool_id: str, field: str, value: str) -> str:
    """Texto de un valor de un parámetro `Literal` en el idioma activo."""
    from pdftool.i18n.keys import choice_key

    return t(choice_key(tool_id, field, value))
