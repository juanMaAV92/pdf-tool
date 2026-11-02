from __future__ import annotations

import base64
import math
import threading
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import flet as ft

from pdftool.core.errors import UserError
from pdftool.core.pages import serialize_plan
from pdftool.i18n import t
from pdftool.tools.organize.logic import read_page_count
from pdftool.tools.organize.params import OrganizeParams
from pdftool.tools.organize.session import PageSession
from pdftool.tools.organize.spec import SPEC
from pdftool.ui.accessibility import NamedIconButton
from pdftool.ui.panel_base import InvalidParams, SingleFileToolPanel
from pdftool.ui.registry import register
from pdftool.ui.thumbnails import load_async

# Medido con escaneos en macOS, con todas las miniaturas: 1000 páginas, 530 MB en
# Python y 0,1 s por edición; 2000 páginas, 960 MB y 0,2 s. La CLI no tiene límite.
MAX_PAGES = 1000
_THUMBNAIL_HEIGHT = 240
_IMAGE_SIDE = 100
_DRAG_GROUP = "organize-page"

FileStamp = tuple[int, int]


def _stamp(path: Path) -> FileStamp:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


class _Opened(NamedTuple):
    """Lo necesario para volver a un PDF al deshacer un cambio de archivo."""

    file: Path
    session: PageSession
    stamp: FileStamp
    thumbnails: dict[int, str | None]


class _PageCell:
    """Una celda fija de la cuadrícula: muestra lo que haya en su posición.

    Mover páginas cambia lo que muestran las celdas, no las celdas.
    """

    def __init__(
        self,
        position: int,
        on_toggle: Callable[[int], None],
        on_drop: Callable[[int, ft.DragTargetEvent], None],
    ) -> None:
        self.source = 0
        self.image = ft.Image(
            width=_IMAGE_SIDE,
            height=_IMAGE_SIDE,
            fit=ft.ImageFit.CONTAIN,
            gapless_playback=True,
            visible=False,
        )
        self.placeholder = ft.Icon(
            ft.Icons.PICTURE_AS_PDF, size=40, color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.check = ft.Checkbox(on_change=lambda _e: on_toggle(position))
        self.number = ft.Text(size=13)
        self.frame = ft.Container(
            ft.Column(
                [
                    ft.Stack(
                        [self.image, self.placeholder],
                        width=_IMAGE_SIDE,
                        height=_IMAGE_SIDE,
                        alignment=ft.alignment.center,
                    ),
                    ft.Row(
                        [self.check, self.number],
                        spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=4,
            border_radius=8,
            on_click=lambda _e: on_toggle(position),
        )
        self.control = ft.DragTarget(
            group=_DRAG_GROUP,
            content=ft.Draggable(group=_DRAG_GROUP, content=self.frame, data=position),
            on_will_accept=self._on_hover,
            on_leave=self._on_leave,
            on_accept=lambda e: on_drop(position, e),
        )

    def show(
        self, position: int, count: int, rotation: int, selected: bool, source: int
    ) -> None:
        self.source = source
        self.number.value = str(position + 1)
        self.check.value = selected
        self.check.semantics_label = (
            t(
                "tool.organize.ui.page_label_rotated",
                position=position + 1,
                count=count,
                degrees=rotation,
            )
            if rotation
            else t("tool.organize.ui.page_label", position=position + 1, count=count)
        )
        self.image.rotate = ft.Rotate(math.radians(rotation))
        self.frame.bgcolor = ft.Colors.PRIMARY_CONTAINER if selected else None
        self.frame.border = (
            ft.border.all(2, ft.Colors.PRIMARY)
            if selected
            else ft.border.all(2, ft.Colors.TRANSPARENT)
        )

    def show_thumbnail(self, encoded: str | None, *, failed: bool) -> None:
        self.image.src_base64 = encoded
        self.image.visible = encoded is not None
        self.placeholder.visible = encoded is None
        self.placeholder.name = (
            ft.Icons.BROKEN_IMAGE_OUTLINED if failed else ft.Icons.PICTURE_AS_PDF
        )

    def _on_hover(self, _e) -> None:
        self.frame.border = ft.border.all(2, ft.Colors.TERTIARY)
        self.frame.update()

    def _on_leave(self, _e) -> None:
        checked = bool(self.check.value)
        self.frame.border = ft.border.all(
            2, ft.Colors.PRIMARY if checked else ft.Colors.TRANSPARENT
        )
        self.frame.update()


@register
class OrganizeTool(SingleFileToolPanel):
    spec = SPEC
    icon = ft.Icons.DASHBOARD_CUSTOMIZE
    run_label_key = "tool.organize.ui.save"
    run_icon = ft.Icons.SAVE_OUTLINED
    pick_label_key = "ui.panel.pick_pdf"
    expand_body_when_ready = True
    input_in_title_when_compact = True
    body_scrolls_itself = True

    def __init__(self) -> None:
        super().__init__()
        self._session: PageSession | None = None
        self._opened_file: Path | None = None
        self._opened_stamp: FileStamp | None = None
        self._extracting = False
        self._thumbnails: dict[int, str | None] = {}
        self._thumbnail_generation = 0
        self._cells: list[_PageCell] = []
        self._cells_by_source: dict[int, list[_PageCell]] = {}
        self._lock = threading.Lock()  # los workers pintan miniaturas en las celdas

    # ---- entrada ----
    def build_input(self, page) -> ft.Control:
        # Página nueva (otra sesión): los controles se rehacen, el archivo también.
        self._session = None
        self._opened_file = None
        self._opened_stamp = None
        self._cells = []
        row = super().build_input(page)
        self._input_row = row
        self._file_label.expand = True
        self._file_label.no_wrap = True
        self._file_label.overflow = ft.TextOverflow.ELLIPSIS
        return row

    def _build_title(self) -> ft.Control:
        # El nombre del archivo comparte fila con el título y se recorta él.
        self._title_input_slot.expand = True
        return ft.Row(
            [
                ft.Text(self.meta.name, size=24, weight=ft.FontWeight.BOLD),
                self._title_input_slot,
            ],
            spacing=16,
        )

    def _apply_density(self, *, compact: bool) -> None:
        super()._apply_density(compact=compact)
        controls = [self._pick_btn, self._file_label]
        self._input_row.controls = controls[::-1] if compact else controls
        self._file_label.text_align = (
            ft.TextAlign.RIGHT if compact else ft.TextAlign.LEFT
        )
        self._pick_btn.text = t(
            "tool.organize.ui.pick_other" if compact else self.pick_label_key
        )

    def after_pick(self, path: Path) -> None:
        previous = self._opened()
        self._thumbnail_generation += 1
        self._session = None
        self._file_label.value = t("tool.organize.ui.reading")
        self._sync_view()

        def read(_progress) -> tuple[int, FileStamp]:
            count = read_page_count(path)
            if count > MAX_PAGES:
                raise UserError(
                    t(
                        "tool.organize.error.too_many",
                        count=count,
                        max=MAX_PAGES,
                        tool=t("tool.split.name"),
                    )
                )
            return count, _stamp(path)

        def on_done(result: tuple[int, FileStamp]) -> None:
            if self._file != path:  # el usuario ya eligió otro archivo
                return
            count, stamp = result
            self._open(_Opened(path, PageSession(count), stamp, {}))
            if previous is not None and not previous.session.is_identity:
                self._notify(
                    t("tool.organize.ui.discarded"),
                    action=t("ui.files.undo"),
                    on_action=lambda _e: self._return_to(previous),
                    duration=8000,
                )
            self._page.update()

        def on_error(exc: Exception) -> None:
            if self._file != path:
                return
            self._reject_pick(exc)
            # Un archivo que no abre no debe costar el trabajo que ya había.
            if previous is not None:
                status = self.status.value
                self._open(previous)
                self._set_status(status, "error")
            self._page.update()

        self._ctx.run_job(
            work=read,
            on_progress=lambda *_: None,
            on_done=on_done,
            on_error=on_error,
        )

    def _opened(self) -> _Opened | None:
        # `_file` ya es el archivo nuevo cuando se llama desde `after_pick`.
        if self._session is None or self._opened_file is None:
            return None
        if self._opened_stamp is None:
            return None
        return _Opened(
            self._opened_file, self._session, self._opened_stamp, self._thumbnails
        )

    def _open(self, opened: _Opened) -> None:
        self._file = opened.file
        self._opened_file = opened.file
        self._session = opened.session
        self._opened_stamp = opened.stamp
        self._thumbnails = opened.thumbnails
        self._file_label.italic = False
        self._file_label.tooltip = opened.file.name  # el texto puede ir recortado
        self._file_label.value = t(
            "tool.organize.ui.file_info",
            name=opened.file.name,
            count=len(opened.session.plan),
        )
        self._close_prompt()
        self._sync_view()
        self._load_thumbnails()

    def _return_to(self, opened: _Opened) -> None:
        self._invalidate_active_job()
        self._hide_result_actions()
        self._set_status("")
        self._open(opened)
        self._page.update()

    def _reject_pick(self, exc: Exception) -> None:
        self._session = None
        self._opened_file = None
        self._opened_stamp = None
        self._thumbnail_generation += 1
        super()._reject_pick(exc)
        self._sync_view()

    # ---- controles ----
    def extra_controls(self) -> list[ft.Control]:
        self._select_all = ft.Checkbox(
            tristate=True,
            tooltip=t("tool.organize.ui.select_all"),
            on_change=lambda _e: self._edit(lambda s: s.cycle_all()),
        )
        self._select_btn = ft.TextButton(
            t("tool.organize.ui.select"),
            on_click=lambda _e: self._open_prompt(
                t("tool.organize.ui.select_prompt"),
                t("tool.organize.ui.select_hint"),
                t("tool.organize.ui.apply"),
                self._apply_selection,
            ),
        )
        self._rotate_left = self._tool_button(
            ft.Icons.ROTATE_LEFT,
            "rotate_left",
            lambda _e: self._edit(lambda s: s.rotate(-90)),
        )
        self._rotate_right = self._tool_button(
            ft.Icons.ROTATE_RIGHT,
            "rotate_right",
            lambda _e: self._edit(lambda s: s.rotate(90)),
        )
        self._move_back = self._tool_button(
            ft.Icons.ARROW_BACK,
            "move_back",
            lambda _e: self._edit(lambda s: s.shift(-1)),
        )
        self._move_forward = self._tool_button(
            ft.Icons.ARROW_FORWARD,
            "move_forward",
            lambda _e: self._edit(lambda s: s.shift(1)),
        )
        self._move_to = self._tool_button(
            ft.Icons.SHORTCUT,
            "move_to",
            lambda _e: self._open_prompt(
                t("tool.organize.ui.move_prompt"),
                "",
                t("tool.organize.ui.move"),
                self._apply_move,
            ),
        )
        self._delete = self._tool_button(
            ft.Icons.DELETE_OUTLINE,
            "delete",
            lambda _e: self._edit(lambda s: s.delete()),
        )
        self._duplicate = self._tool_button(
            ft.Icons.CONTENT_COPY,
            "duplicate",
            lambda _e: self._edit(lambda s: s.duplicate()),
        )
        self._reverse = self._tool_button(
            ft.Icons.SWAP_VERT, "reverse", lambda _e: self._edit(lambda s: s.reverse())
        )
        self._toolbar = ft.Row(
            [
                self._select_all,
                self._select_btn,
                self._rotate_left,
                self._rotate_right,
                self._move_back,
                self._move_forward,
                self._move_to,
                self._delete,
                self._duplicate,
                self._reverse,
            ],
            spacing=0,
            visible=False,
        )
        self._prompt_label = ft.Text()
        self._prompt_field = ft.TextField(
            width=110, dense=True, on_submit=lambda _e: self._prompt_apply()
        )
        self._prompt_action = ft.TextButton(on_click=lambda _e: self._prompt_apply())
        self._prompt_apply: Callable[[], None] = lambda: None
        self._prompt = ft.Row(
            [
                self._prompt_label,
                self._prompt_field,
                self._prompt_action,
                ft.TextButton(
                    t("ui.panel.cancel"),
                    on_click=lambda _e: self._cancel_prompt(),
                ),
            ],
            spacing=8,
            visible=False,
        )
        return [self._toolbar, self._prompt]

    @staticmethod
    def _tool_button(icon, key: str, on_click) -> NamedIconButton:
        return NamedIconButton(icon, t(f"tool.organize.ui.{key}"), on_click=on_click)

    def extra_actions(self) -> list[ft.Control]:
        self._extract_btn = ft.OutlinedButton(
            t("tool.organize.ui.extract"),
            icon=ft.Icons.OUTPUT,
            on_click=self._on_extract,
            visible=False,
        )
        self._undo_btn = ft.TextButton(
            t("tool.organize.ui.undo"),
            icon=ft.Icons.UNDO,
            on_click=lambda _e: self._edit(lambda s: s.undo()),
            visible=False,
        )
        return [self._extract_btn, self._undo_btn]

    def build_body(self) -> ft.Control:
        self._grid = ft.GridView(
            max_extent=150,
            spacing=12,
            run_spacing=12,
            child_aspect_ratio=0.85,
            expand=True,
            padding=ft.padding.only(right=8),
            visible=False,
        )
        return self._grid

    # ---- estado -> controles ----
    def _is_loaded(self) -> bool:
        return self._session is not None

    def can_run(self) -> bool:
        if self._session is None:
            return False
        if self._extracting:
            return bool(self._session.selection)
        return not self._session.is_identity

    def _empty_action_hint(self) -> str:
        if self._session is not None:
            return t("tool.organize.ui.need_change")
        return super()._empty_action_hint()

    def _sync_view(self) -> None:
        """Deja todos los controles como dicta la sesión."""
        session = self._session
        loaded = session is not None
        self._grid.visible = loaded
        self._toolbar.visible = loaded and not self._prompt.visible
        self._extract_btn.visible = loaded
        self._undo_btn.visible = loaded
        if session is None:
            self._counter.value = ""
            self._sync_ready_state()
            return
        self._sync_cells(session)
        self._sync_toolbar(session)
        self._sync_ready_state()

    def _sync_cells(self, session: PageSession) -> None:
        count = len(session.plan)
        with self._lock:
            while len(self._cells) < count:
                self._cells.append(
                    _PageCell(len(self._cells), self._on_toggle, self._on_drop)
                )
            self._grid.controls = [cell.control for cell in self._cells[:count]]
            by_source: dict[int, list[_PageCell]] = defaultdict(list)
            for position, (page, rotation) in enumerate(session.plan):
                cell = self._cells[position]
                source = page - 1
                cell.show(
                    position, count, rotation, position in session.selection, source
                )
                by_source[source].append(cell)
                if source in self._thumbnails:
                    encoded = self._thumbnails[source]
                    cell.show_thumbnail(encoded, failed=encoded is None)
                else:
                    cell.show_thumbnail(None, failed=False)
            self._cells_by_source = by_source

    def _sync_toolbar(self, session: PageSession) -> None:
        running = self._running
        has_selection = bool(session.selection)
        self._select_all.value = {"none": False, "all": True}.get(
            session.selection_state
        )
        for control in (self._select_all, self._select_btn, self._reverse):
            control.disabled = running
        for control in (
            self._rotate_left,
            self._rotate_right,
            self._move_to,
            self._delete,
            self._duplicate,
        ):
            control.disabled = running or not has_selection
        self._move_back.disabled = running or not session.can_shift(-1)
        self._move_forward.disabled = running or not session.can_shift(1)
        self._extract_btn.disabled = running or not has_selection
        self._undo_btn.disabled = running or not session.can_undo
        self._counter.value = t(
            "tool.organize.ui.counter",
            selected=len(session.selection),
            count=len(session.plan),
        )

    def _lock_inputs(self, locked: bool) -> None:
        super()._lock_inputs(locked)
        self._grid.disabled = locked
        if self._session is not None:
            self._sync_toolbar(self._session)
        if locked:
            # Exportar compite con las miniaturas por CPU y por el GIL.
            self._thumbnail_generation += 1
        else:
            self._load_thumbnails()

    # ---- edición ----
    def _edit(self, change: Callable[[PageSession], None]) -> None:
        if self._session is None or self._running:
            return
        self._hide_result_actions()
        self._clear_error()
        self._set_status("")
        try:
            change(self._session)
        except UserError as exc:
            self._set_status(str(exc), "error")
        self._sync_view()
        self._page.update()

    def _on_toggle(self, position: int) -> None:
        if self._session is None or self._running:
            return
        self._edit(lambda s: s.toggle(position))

    def _on_drop(self, target: int, event: ft.DragTargetEvent) -> None:
        source = self._page.get_control(event.src_id).data
        if source != target:
            self._edit(lambda s: s.drag(source, target))
        else:
            self._sync_view()
            self._page.update()

    def _on_extract(self, _e) -> None:
        # Solo dura lo que tarda en validarse: el trabajo ya lleva sus params.
        self._extracting = True
        try:
            self._on_run_click(None)
        finally:
            self._extracting = False
        self._sync_ready_state()
        self._page.update()

    # ---- entrada de número en la barra ----
    def _open_prompt(
        self, label: str, hint: str, action: str, apply: Callable[[], None]
    ) -> None:
        self._prompt_label.value = label
        self._prompt_field.hint_text = hint
        self._prompt_field.value = ""
        self._prompt_action.text = action
        self._prompt_apply = apply
        self._prompt.visible = True
        self._toolbar.visible = False
        self._page.update()

    def _close_prompt(self) -> None:
        self._prompt.visible = False
        self._toolbar.visible = self._session is not None

    def _cancel_prompt(self) -> None:
        self._close_prompt()
        self._set_status("")
        self._page.update()

    def _apply_prompt(self, change: Callable[[PageSession], None]) -> None:
        if self._session is None:
            return
        self._set_status("")
        self._hide_result_actions()
        try:
            change(self._session)
        except UserError as exc:
            # El error va abajo: un error_text cambiaría la altura de la barra.
            self._set_status(str(exc), "error")
            self._page.update()
            return
        self._close_prompt()
        self._sync_view()
        self._page.update()

    def _apply_selection(self) -> None:
        spec = self._prompt_field.value or ""
        self._apply_prompt(lambda s: s.select_spec(spec))

    def _apply_move(self) -> None:
        text = (self._prompt_field.value or "").strip()

        def change(session: PageSession) -> None:
            last = len(session.plan) - len(session.selection) + 1
            if not text.isdecimal():
                raise UserError(t("tool.organize.error.bad_position", last=last))
            session.move_to_position(int(text))

        self._apply_prompt(change)

    # ---- miniaturas ----
    def _load_thumbnails(self) -> None:
        if self._file is None or self._session is None or self._running:
            return
        self._thumbnail_generation += 1
        generation = self._thumbnail_generation
        path = self._file
        sources = sorted({page - 1 for page, _ in self._session.plan})
        missing = [
            (path, source) for source in sources if source not in self._thumbnails
        ]
        if not missing:
            return
        dirty: set[int] = set()

        def on_ready(item: tuple[Path, int], data: bytes | None) -> None:
            source = item[1]
            encoded = None if data is None else base64.b64encode(data).decode()
            with self._lock:
                self._thumbnails[source] = encoded
                for cell in self._cells_by_source.get(source, ()):
                    cell.show_thumbnail(encoded, failed=encoded is None)
                dirty.add(source)

        def flush() -> None:
            with self._lock:
                frames = [
                    cell.frame
                    for source in dirty
                    for cell in self._cells_by_source.get(source, ())
                ]
                dirty.clear()
            if frames:
                self._page.update(*frames)

        load_async(
            missing,
            on_ready,
            is_current=lambda: generation == self._thumbnail_generation,
            on_flush=flush,
            height_px=_THUMBNAIL_HEIGHT,
            fmt="jpg",
        )

    # ---- guardar ----
    def _show_result_actions(self, result) -> None:
        super()._show_result_actions(result)
        # En la ventana mínima el resultado dejaría menos de una fila de páginas.
        self._out_dir.visible = False

    def _hide_result_actions(self) -> None:
        super()._hide_result_actions()
        self._out_dir.visible = True

    def make_params(self):
        session = self._session
        if session is None or self._file is None:
            raise InvalidParams(t("ui.panel.need_one"))
        try:
            unchanged = _stamp(self._file) == self._opened_stamp
        except FileNotFoundError as exc:
            raise InvalidParams(t("core.error.file_not_found")) from exc
        if not unchanged:
            raise InvalidParams(t("tool.organize.error.changed"))
        plan = session.extract_plan() if self._extracting else session.plan
        return OrganizeParams(pages=serialize_plan(plan))
