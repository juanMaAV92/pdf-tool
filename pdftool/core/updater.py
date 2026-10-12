from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable, Optional

GITHUB_REPO = "juanMaAV92/pdf-tool"

# La respuesta de /releases/latest pesa unos KB; un tope evita leer sin límite.
_MAX_RESPONSE_BYTES = 1_000_000
# vX.Y.Z con sufijo opcional de preversión/metadatos.
_TAG = re.compile(r"^v?\d+(\.\d+){0,3}([-+][0-9A-Za-z.-]+)?$")


def _parse(version: str) -> tuple[int, ...]:
    # Toma los dígitos iniciales de cada segmento e ignora sufijos (p.ej.
    # "0-beta" -> 0), para no reventar con tags de preversión.
    parts = version.lstrip("vV").split(".")
    return tuple(
        (int(m.group()) if (m := re.match(r"\d+", part)) else 0) for part in parts
    )


def is_newer(latest: str, current: str) -> bool:
    a, b = _parse(latest), _parse(current)
    # Rellena con ceros para comparar "1.2" y "1.2.0" como iguales.
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return a > b


def _default_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=5) as resp:  # URL https fija
        body = resp.read(_MAX_RESPONSE_BYTES + 1)
    if len(body) > _MAX_RESPONSE_BYTES:
        raise ValueError("Respuesta de GitHub demasiado grande")
    return json.loads(body.decode("utf-8"))


def check_for_update(
    current: str, repo: str, http_get: Callable[[str], dict] = _default_get
) -> Optional[str]:
    """Devuelve la URL del release si hay una versión más nueva, si no None.

    Nunca lanza: ante cualquier error (offline, formato raro) devuelve None.
    La URL solo se acepta si es una página de releases de `repo` en GitHub:
    la app la abre en el navegador, así que no debe poder ser otra cosa.
    """
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = http_get(url)
        tag, html_url = data["tag_name"], data["html_url"]
        if not (isinstance(tag, str) and _TAG.match(tag)):
            return None
        if not (
            isinstance(html_url, str)
            and html_url.startswith(f"https://github.com/{repo}/releases/")
        ):
            return None
        if is_newer(tag, current):
            return html_url
        return None
    except Exception:  # el chequeo de update nunca debe romper la app
        return None
