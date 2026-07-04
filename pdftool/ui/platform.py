from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_folder(path: Path) -> None:
    """Abre el gestor de archivos del sistema en `path`."""
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(path))  # noqa: S606  (Windows-only)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)
