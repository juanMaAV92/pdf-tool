from __future__ import annotations

import json
import urllib.request
from typing import Callable, Optional


def _parse(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.lstrip("vV").split("."))


def is_newer(latest: str, current: str) -> bool:
    return _parse(latest) > _parse(current)


def _default_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def check_for_update(current: str, repo: str,
                     http_get: Callable[[str], dict] = _default_get) -> Optional[str]:
    """Devuelve la URL del release si hay una versión más nueva, si no None.

    Nunca lanza: ante cualquier error (offline, formato raro) devuelve None.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = http_get(url)
        if is_newer(data["tag_name"], current):
            return data["html_url"]
        return None
    except Exception:  # noqa: BLE001 - el chequeo de update nunca debe romper la app
        return None
