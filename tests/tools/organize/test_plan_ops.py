import pytest

from pdftool.core.errors import UserError
from pdftool.tools.organize.logic import (
    delete,
    duplicate,
    extract,
    identity_plan,
    move_to,
    reverse,
    rotate,
    shift,
)


def _plan(*pages):
    return [(page, 0) for page in pages]


def test_identity_plan():
    assert identity_plan(3) == [(1, 0), (2, 0), (3, 0)]


def test_rotate_accumulates_and_wraps_only_selected():
    plan = [(1, 270), (2, 0), (3, 0)]
    assert rotate(plan, [0, 2], 90) == [(1, 0), (2, 0), (3, 90)]
    assert rotate(plan, [1], -90) == [(1, 270), (2, 270), (3, 0)]


@pytest.mark.parametrize(
    ("positions", "target", "expected"),
    [
        ([0], 3, [2, 3, 1, 4]),  # hueco antes del elemento 3
        ([3], 0, [4, 1, 2, 3]),
        ([0], 4, [2, 3, 4, 1]),  # hueco final
        ([0, 2], 4, [2, 4, 1, 3]),  # no contiguas: conservan su orden
        ([2, 0], 4, [2, 4, 1, 3]),  # el orden de los clics no importa
        ([1, 2], 2, [1, 2, 3, 4]),  # soltar dentro de la selección: nada
        ([1], 1, [1, 2, 3, 4]),
        ([1], 2, [1, 2, 3, 4]),
    ],
)
def test_move_to(positions, target, expected):
    assert move_to(_plan(1, 2, 3, 4), positions, target) == _plan(*expected)


@pytest.mark.parametrize(
    ("positions", "direction", "expected"),
    [
        ([1], -1, [2, 1, 3, 4]),
        ([1], 1, [1, 3, 2, 4]),
        ([0], -1, [1, 2, 3, 4]),  # borde
        ([3], 1, [1, 2, 3, 4]),  # borde
        ([0, 1], -1, [1, 2, 3, 4]),  # bloque en el borde: no se deforma
        ([2, 3], 1, [1, 2, 3, 4]),
        ([1, 2], 1, [1, 4, 2, 3]),
        ([0, 2], 1, [2, 1, 4, 3]),  # no contiguas: cada una avanza
        ([1, 3], -1, [2, 1, 4, 3]),
    ],
)
def test_shift(positions, direction, expected):
    assert shift(_plan(1, 2, 3, 4), positions, direction) == _plan(*expected)


def test_reverse_keeps_rotations():
    assert reverse([(1, 90), (2, 0)]) == [(2, 0), (1, 90)]


def test_duplicate_goes_right_after_each_selected():
    assert duplicate([(1, 90), (2, 0), (3, 0)], [0, 2]) == [
        (1, 90),
        (1, 90),
        (2, 0),
        (3, 0),
        (3, 0),
    ]


def test_delete_removes_selected():
    assert delete(_plan(1, 2, 3), [0, 2]) == _plan(2)


def test_delete_everything_is_refused():
    with pytest.raises(UserError, match="al menos una página"):
        delete(_plan(1, 2), [0, 1])


def test_extract_keeps_plan_order_not_click_order():
    assert extract(_plan(3, 1, 2), [2, 0]) == _plan(3, 2)


def test_operations_do_not_mutate_their_input():
    plan = _plan(1, 2, 3)
    for result in (
        rotate(plan, [0], 90),
        move_to(plan, [0], 3),
        shift(plan, [0], 1),
        reverse(plan),
        duplicate(plan, [0]),
        delete(plan, [0]),
        extract(plan, [0]),
    ):
        assert result is not plan
    assert plan == _plan(1, 2, 3)
