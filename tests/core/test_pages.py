import random

import pytest

from pdftool.core.errors import UserError
from pdftool.core.pages import parse_plan, parse_selection, serialize_plan
from pdftool.tools.split.logic import parse_ranges, resolve_ranges


def _pages(*numbers: int, rotation: int = 0) -> list[tuple[int, int]]:
    return [(n, rotation) for n in numbers]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("3", _pages(3)),
        ("2-4", _pages(2, 3, 4)),
        ("4-2", _pages(4, 3, 2)),
        ("3-3", _pages(3)),
        ("4-", _pages(4, 5)),
        ("-2", _pages(1, 2)),
        ("end", _pages(5)),
        ("end-1", _pages(5, 4, 3, 2, 1)),
        ("end-2", _pages(5, 4, 3, 2)),
        ("end-5", _pages(5)),
        ("2-end", _pages(2, 3, 4, 5)),
        ("END-1", _pages(5, 4, 3, 2, 1)),
        ("2@90", _pages(2, rotation=90)),
        ("1-2@180", _pages(1, 2, rotation=180)),
        ("2-1@270", _pages(2, 1, rotation=270)),
        ("end@90", _pages(5, rotation=90)),
        ("1,1,1", _pages(1, 1, 1)),
        ("3,1", _pages(3, 1)),
        (" 1 - 2 , end @ 90 ,", [(1, 0), (2, 0), (5, 90)]),
        ("1,,2", _pages(1, 2)),
    ],
)
def test_parse_plan_grammar(spec, expected):
    assert parse_plan(spec, 5) == expected


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("", "Indica al menos una página"),
        ("  ,  ", "Indica al menos una página"),
        ("a", "«a» no es un número de página válido"),
        ("1-a", "«a» no es un número de página válido"),
        ("-", "«-» no es un rango válido"),
        ("1-2-3", "«1-2-3» no es un rango válido"),
        ("end-", "«end-» no es un rango válido"),
        ("-end", "«-end» no es un rango válido"),
        ("@90", "«@90» no es un rango válido"),
        ("0", "Las páginas empiezan en 1"),
        ("0-2", "Las páginas empiezan en 1"),
        ("6", "La página 6 no existe: este PDF tiene 5 páginas"),
        ("6-", "La página 6 no existe"),
        ("-6", "La página 6 no existe"),
        ("9-1", "La página 9 no existe"),
        ("1@0", r"La rotación debe ser @90, @180 o @270 \(«1@0»\)"),
        ("1@45", "La rotación debe ser"),
        ("1@-90", "La rotación debe ser"),
        ("1@", "La rotación debe ser"),
        ("1@90@90", "La rotación debe ser"),
        ("9" * 5000, "no es un número de página válido"),
    ],
)
def test_parse_plan_errors(spec, message):
    with pytest.raises(UserError, match=message):
        parse_plan(spec, 5)


def test_out_of_bounds_uses_the_singular_for_a_one_page_pdf():
    with pytest.raises(UserError, match="este PDF tiene 1 página\\."):
        parse_plan("2", 1)


@pytest.mark.parametrize(
    ("plan", "expected"),
    [
        (_pages(1, 2, 3), "1-3"),
        (_pages(3, 2, 1), "3-1"),
        (_pages(1, 3), "1,3"),
        (_pages(2, 2), "2,2"),
        ([(1, 90), (2, 90), (3, 0)], "1-2@90,3"),
        ([(1, 90), (2, 180)], "1@90,2@180"),
        (_pages(1, 2, 1), "1-2,1"),
        ([], ""),
    ],
)
def test_serialize_plan_compresses_runs(plan, expected):
    assert serialize_plan(plan) == expected


def test_serialized_plan_parses_back_to_the_same_plan():
    rng = random.Random(20261102)
    for _ in range(500):
        count = rng.randint(1, 30)
        plan = [
            (rng.randint(1, count), rng.choice((0, 0, 0, 90, 180, 270)))
            for _ in range(rng.randint(1, 40))
        ]
        assert parse_plan(serialize_plan(plan), count) == plan


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("3", [3]),
        ("2-4", [2, 3, 4]),
        ("4-", [4, 5]),
        ("-2", [1, 2]),
        ("1, 3,", [1, 3]),
        ("3,1,3,1-2", [3, 1, 2]),
    ],
)
def test_parse_selection(spec, expected):
    assert parse_selection(spec, 5) == expected


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("", "Indica al menos una página"),
        ("4-2", "El rango «4-2» está al revés"),
        ("end", "«end» no es un número de página válido"),
        ("end-1", "«end» no es un número de página válido"),
        ("1@90", "«1@90» no es un número de página válido"),
        ("0", "Las páginas empiezan en 1"),
        ("6", "La página 6 no existe"),
        ("1-2-3", "no es un rango válido"),
    ],
)
def test_parse_selection_is_strict(spec, message):
    with pytest.raises(UserError, match=message):
        parse_selection(spec, 5)


def _split_pages(spec: str, count: int) -> list[int]:
    seen: dict[int, None] = {}
    for start, end in resolve_ranges(parse_ranges(spec), count):
        seen.update(dict.fromkeys(range(start, end + 1)))
    return list(seen)


@pytest.mark.parametrize("spec", ["1", "1-3", "2-", "-2", "1 - 2 , 4,", "5,1", "1,,3"])
def test_selection_resolves_what_split_accepts_to_the_same_pages(spec):
    assert parse_selection(spec, 5) == _split_pages(spec, 5)


def test_selection_matches_split_on_generated_specs():
    rng = random.Random(7)
    for _ in range(300):
        tokens = []
        for _ in range(rng.randint(1, 5)):
            a, b = sorted((rng.randint(1, 20), rng.randint(1, 20)))
            tokens.append(rng.choice((f"{a}", f"{a}-{b}", f"{a}-", f"-{b}")))
        spec = ",".join(tokens)
        assert parse_selection(spec, 20) == _split_pages(spec, 20)
