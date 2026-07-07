from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable, Optional


def _parse(version: str) -> tuple[int, ...]:
    # Toma los dígitos iniciales de cada segmento e ignora sufijos (p.ej.
    # "0-beta" -> 0), para no reventar con tags de preversión.
    parts = version.lstrip("vV").split(".")
    return tuple((int(m.group()) if (m := re.match(r"\d+", part)) else 0)
                 for part in parts)


def is_newer(latest: str, current: str) -> bool:
    a, b = _parse(latest), _parse(current)
    # Rellena con ceros para comparar "1.2" y "1.2.0" como iguales.
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return a > b


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
