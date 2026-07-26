from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import flet as ft

from pdftool.core.config import Settings, save_settings

_DEFAULT_LABEL = "Junto al original"


def abbreviate_home(path: Path) -> str:
    """Ruta legible: «~/Desktop» en vez de «/Users/quien/Desktop»."""
    try:
        rel = path.relative_to(Path.home())
    except ValueError:
        return str(path)
    return "~" if rel == Path(".") else f"~/{rel}"


class OutputDirField(ft.Row):
    """Selector del destino de las salidas: junto al original o una carpeta.

    El estado es global y vive en `Settings`; se persiste en cuanto cambia, no
    al ejecutar. Si la carpeta guardada ya no existe (disco desconectado,
    carpeta borrada), se vuelve al default en silencio.
    """

    def __init__(self, settings: Settings | None,
                 on_change: Callable[[], None] | None = None,
                 settings_path: Path | None = None) -> None:
        # Sin Settings real (p. ej. tests que no pasan ctx.settings), el
        # widget usa una privada solo para no romper pero nunca persiste:
        # de lo contrario `set_dir` escribiría en el settings.json real.
        self._persist = settings is not None
        self._settings = settings if settings is not None else Settings()
        self._on_change = on_change
        # Público a propósito: los tests lo redirigen a un tmp_path para no
        # escribir en el settings.json real del usuario. None → el de la app.
        self.settings_path = settings_path
        self._dir = self._restore()

        self.label = ft.Text(_DEFAULT_LABEL, max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.change_btn = ft.TextButton("Cambiar…", icon=ft.Icons.FOLDER_OPEN,
                                        on_click=self._pick)
        self.reset_btn = ft.IconButton(ft.Icons.UNDO,
                                       tooltip="Volver a «junto al original»",
                                       on_click=lambda _e: self.set_dir(None))
        self._picker = ft.FilePicker(on_result=self._on_pick_result)

        super().__init__([ft.Text("Guardar en:"), self.label,
                          self.change_btn, self.reset_btn])
        self._render()

    # ---- estado ----
    @property
    def value(self) -> Path | None:
        return self._dir

    def set_dir(self, path: Path | None) -> None:
        """Fija el destino, lo persiste y avisa al panel."""
        self._dir = path
        self._settings.output_dir = str(path) if path is not None else None
        if self._persist:
            save_settings(self._settings, self.settings_path)
        self._render()
        if self.page:
            self.update()
        if self._on_change:
            self._on_change()

    def attach(self, page) -> None:
        """Registra el picker en el overlay una sola vez."""
        if self._picker not in page.overlay:
            page.overlay.append(self._picker)

    def sync(self) -> None:
        """Re-lee el destino de `Settings`. Lo llama el panel en cada render,
        porque el widget sobrevive entre navegaciones y otro panel puede haber
        cambiado el destino mientras tanto."""
        self._dir = self._restore()
        self._render()
        if self.page:
            self.update()

    def destination_missing(self) -> bool:
        """True si hay un destino elegido y ya no es una carpeta accesible."""
        return self._dir is not None and not self._dir.is_dir()

    # ---- interno ----
    def _restore(self) -> Path | None:
        guardado = self._settings.output_dir
        if not guardado:
            return None
        path = Path(guardado)
        if path.is_dir():
            return path
        # La carpeta ya no está: al default, sin molestar al usuario.
        self._settings.output_dir = None
        if self._persist:
            save_settings(self._settings, self.settings_path)
        return None

    def _render(self) -> None:
        self.label.value = (_DEFAULT_LABEL if self._dir is None
                            else abbreviate_home(self._dir))
        self.label.tooltip = None if self._dir is None else str(self._dir)
        self.reset_btn.visible = self._dir is not None

    def _pick(self, _e) -> None:
        self._picker.get_directory_path(dialog_title="Guardar las salidas en…")

    def _on_pick_result(self, e) -> None:
        if e.path:
            self.set_dir(Path(e.path))
