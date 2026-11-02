from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pdftool.core.errors import UserError
from pdftool.core.pages import Plan, parse_selection
from pdftool.i18n import t
from pdftool.tools.organize import logic

MAX_UNDO = 100

SelectionState = Literal["none", "partial", "all"]


class PageSession:
    """La edición en curso de un PDF, sin UI: plan, selección y deshacer.

    Las posiciones son índices del plan actual, base 0.
    """

    def __init__(self, page_count: int) -> None:
        self.plan: Plan = logic.identity_plan(page_count)
        self.selection: set[int] = set()
        self._identity = list(self.plan)
        self._undo: list[Plan] = []

    @property
    def is_identity(self) -> bool:
        return self.plan == self._identity

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def selection_state(self) -> SelectionState:
        if not self.selection:
            return "none"
        return "all" if len(self.selection) == len(self.plan) else "partial"

    def toggle(self, position: int) -> None:
        self.selection ^= {position}

    def cycle_all(self) -> None:
        """Sin selección -> todas; con alguna -> ninguna."""
        self.selection = set(range(len(self.plan))) if not self.selection else set()

    def select_spec(self, spec: str) -> None:
        pages = parse_selection(spec, len(self.plan))
        self.selection = {page - 1 for page in pages}

    def can_shift(self, direction: int) -> bool:
        return any(
            0 <= position + direction < len(self.plan)
            and position + direction not in self.selection
            for position in self.selection
        )

    def rotate(self, delta: int) -> None:
        self._change(logic.rotate(self.plan, self._selected(), delta), self.selection)

    def shift(self, direction: int) -> None:
        positions = self._selected()
        self._rearrange(lambda plan: logic.shift(plan, positions, direction))

    def move_to_position(self, position: int) -> None:
        """El bloque elegido empieza en la posición `position` (base 1) del resultado."""
        count = len(self.plan)
        last = count - len(self.selection) + 1
        if not 1 <= position <= last:
            raise UserError(t("tool.organize.error.bad_position", last=last))
        rest = [index for index in range(count) if index not in self.selection]
        before = rest[position - 2] + 1 if position > 1 else 0
        positions = self._selected()
        self._rearrange(lambda plan: logic.move_to(plan, positions, before))

    def reverse(self) -> None:
        self._rearrange(logic.reverse)

    def duplicate(self) -> None:
        positions = self._selected()
        selection = {position + index for index, position in enumerate(positions)}
        self._change(logic.duplicate(self.plan, positions), selection)

    def delete(self) -> None:
        self._change(logic.delete(self.plan, self._selected()), set())

    def extract_plan(self) -> Plan:
        return logic.extract(self.plan, self._selected())

    def drag(self, source: int, target: int) -> None:
        """La página arrastrada pasa a ocupar la posición de la de destino."""
        gap = target if source > target else target + 1
        self._rearrange(lambda plan: logic.move_to(plan, [source], gap))

    def undo(self) -> None:
        self.plan = self._undo.pop()
        self.selection = set()

    def _selected(self) -> list[int]:
        return sorted(self.selection)

    def _rearrange(self, operation: Callable[[Plan], Plan]) -> None:
        """Aplica un cambio de orden; la selección sigue a sus páginas."""
        tagged = [(index, 0) for index in range(len(self.plan))]
        order = [index for index, _ in operation(tagged)]
        self._change(
            [self.plan[index] for index in order],
            {
                position
                for position, index in enumerate(order)
                if index in self.selection
            },
        )

    def _change(self, plan: Plan, selection: set[int]) -> None:
        if plan != self.plan:
            self._undo.append(self.plan)
            del self._undo[:-MAX_UNDO]
            self.plan = plan
        self.selection = selection
