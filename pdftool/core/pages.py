from __future__ import annotations

from pdftool.core.errors import UserError
from pdftool.i18n import t

# (página de origen 1-indexada, rotación relativa y horaria: 0, 90, 180 o 270).
Plan = list[tuple[int, int]]

_ROTATIONS = {"90": 90, "180": 180, "270": 270}
_END = "end"


def parse_plan(spec: str, page_count: int) -> Plan:
    """Convierte un plan de texto en la lista de páginas del PDF de salida.

    Tokens separados por comas, sin distinguir mayúsculas: ``N``, ``N-M``,
    ``M-N`` (descendente), ``N-``, ``-M``, ``end``, ``end-N`` y ``N-end``, con un
    ``@90``, ``@180`` o ``@270`` opcional. No hay aritmética: ``end-2`` significa
    «de la última hasta la 2». Una página puede repetirse.
    """
    plan: Plan = []
    for token in _tokens(spec):
        pages_text, rotation = _split_rotation(token)
        first, last = _plan_range(pages_text, token, page_count)
        step = 1 if first <= last else -1
        plan += [(page, rotation) for page in range(first, last + step, step)]
    return plan


def serialize_plan(plan: Plan) -> str:
    """Escribe el plan en su forma más corta; `parse_plan` lo devuelve igual."""
    tokens: list[str] = []
    index = 0
    while index < len(plan):
        first, rotation = plan[index]
        stop = _run_stop(plan, index)
        last = plan[stop - 1][0]
        pages = str(first) if stop == index + 1 else f"{first}-{last}"
        tokens.append(f"{pages}@{rotation}" if rotation else pages)
        index = stop
    return ",".join(tokens)


def parse_selection(spec: str, page_count: int) -> list[int]:
    """Páginas elegidas, sin repetir y en el orden en que aparecen.

    Solo ``N``, ``N-M``, ``N-`` y ``-M``, como Dividir: seleccionar no admite
    orden descendente, ``end`` ni rotación.
    """
    pages: dict[int, None] = {}
    for token in _tokens(spec):
        first, last = _selection_range(token, page_count)
        pages.update(dict.fromkeys(range(first, last + 1)))
    return list(pages)


def _tokens(spec: str) -> list[str]:
    tokens = [token.strip().lower() for token in spec.split(",")]
    tokens = [token for token in tokens if token]  # tolera comas sobrantes
    if not tokens:
        raise UserError(t("core.pages.error.empty"))
    return tokens


def _split_rotation(token: str) -> tuple[str, int]:
    pages_text, separator, angle = token.partition("@")
    if not separator:
        return token, 0
    if not pages_text.strip():
        raise UserError(t("core.pages.error.bad_range", token=token))
    rotation = _ROTATIONS.get(angle.strip())
    if rotation is None:
        raise UserError(t("core.pages.error.bad_rotation", token=token))
    return pages_text.strip(), rotation


def _plan_range(text: str, token: str, page_count: int) -> tuple[int, int]:
    if "-" not in text:
        page = _plan_page(text, page_count)
        return page, page
    left, right = _sides(text, token)
    open_ended = not left or not right
    if (not left and not right) or (open_ended and _END in (left, right)):
        raise UserError(t("core.pages.error.bad_range", token=token))
    first = _plan_page(left, page_count) if left else 1
    last = _plan_page(right, page_count) if right else page_count
    return first, last


def _selection_range(token: str, page_count: int) -> tuple[int, int]:
    if "-" not in token:
        page = _page(token, page_count)
        return page, page
    left, right = _sides(token, token)
    if not left and not right:
        raise UserError(t("core.pages.error.bad_range", token=token))
    first = _page(left, page_count) if left else 1
    last = _page(right, page_count) if right else page_count
    if first > last:
        raise UserError(t("core.pages.error.reversed", token=token))
    return first, last


def _sides(text: str, token: str) -> tuple[str, str]:
    parts = text.split("-")
    if len(parts) != 2:
        raise UserError(t("core.pages.error.bad_range", token=token))
    return parts[0].strip(), parts[1].strip()


def _plan_page(text: str, page_count: int) -> int:
    return page_count if text == _END else _page(text, page_count)


def _page(text: str, page_count: int) -> int:
    try:
        page = int(text) if text.isdecimal() else None
    except ValueError:  # más dígitos de los que `int` admite convertir
        page = None
    if page is None:
        raise UserError(t("core.pages.error.bad_page", text=text))
    if page < 1:
        raise UserError(t("core.pages.error.first_page"))
    if page > page_count:
        raise UserError(
            t("core.pages.error.out_of_bounds", page=page, count=page_count)
        )
    return page


def _run_stop(plan: Plan, start: int) -> int:
    """Fin (exclusivo) del tramo consecutivo con la misma rotación desde `start`."""
    first, rotation = plan[start]
    stop = start + 1
    if stop == len(plan) or plan[stop][1] != rotation:
        return stop
    step = plan[stop][0] - first
    if abs(step) != 1:
        return stop
    while stop < len(plan) and plan[stop] == (plan[stop - 1][0] + step, rotation):
        stop += 1
    return stop
