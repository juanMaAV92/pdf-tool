from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _open_with_system(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_folder(path: Path) -> None:
    """Abre el gestor de archivos del sistema en `path`."""
    _open_with_system(path)


def open_file(path: Path) -> None:
    """Abre `path` con la aplicación por defecto del sistema."""
    _open_with_system(path)
