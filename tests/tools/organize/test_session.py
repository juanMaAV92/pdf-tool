import pytest

from pdftool.core.errors import UserError
from pdftool.tools.organize.session import PageSession


def _pages(session):
    return [page for page, _ in session.plan]


def test_starts_as_identity_without_selection():
    session = PageSession(3)
    assert session.plan == [(1, 0), (2, 0), (3, 0)]
    assert session.selection == set()
    assert session.is_identity
    assert not session.can_undo


# ---- selección ----


def test_toggle_and_tristate():
    session = PageSession(3)
    assert session.selection_state == "none"
    session.toggle(1)
    assert session.selection_state == "partial"
    session.toggle(1)
    assert session.selection_state == "none"


def test_tristate_click_selects_all_only_from_none():
    session = PageSession(2)
    session.cycle_all()
    assert session.selection == {0, 1}
    assert session.selection_state == "all"
    session.cycle_all()
    assert session.selection == set()
    session.toggle(0)
    session.cycle_all()  # parcial -> ninguna
    assert session.selection == set()


def test_select_spec_uses_current_positions_and_strict_syntax():
    session = PageSession(4)
    session.reverse()
    session.select_spec("1-2, 4")
    assert session.selection == {0, 1, 3}
    with pytest.raises(UserError):
        session.select_spec("3-1")
    with pytest.raises(UserError):
        session.select_spec("1@90")
    with pytest.raises(UserError):
        session.select_spec("9")
    assert session.selection == {0, 1, 3}


# ---- operaciones ----


def test_rotate_keeps_selection_and_undo_restores():
    session = PageSession(2)
    session.toggle(0)
    session.rotate(90)
    assert session.plan == [(1, 90), (2, 0)]
    assert session.selection == {0}
    assert not session.is_identity
    session.undo()
    assert session.plan == [(1, 0), (2, 0)]
    assert session.selection == set()  # al deshacer se limpia


def test_full_rotation_is_identity_again():
    session = PageSession(1)
    session.toggle(0)
    for _ in range(4):
        session.rotate(90)
    assert session.is_identity
    assert session.can_undo


def test_shift_selection_follows_pages():
    session = PageSession(4)
    session.toggle(1)
    session.shift(1)
    assert _pages(session) == [1, 3, 2, 4]
    assert session.selection == {2}


@pytest.mark.parametrize(
    ("selected", "backward", "forward"),
    [
        ([], False, False),
        ([0], False, True),
        ([3], True, False),
        ([0, 1], False, True),
        ([2, 3], True, False),
        ([0, 3], True, True),  # cada una puede en un sentido
        ([0, 1, 2, 3], False, False),
    ],
)
def test_can_shift(selected, backward, forward):
    session = PageSession(4)
    for position in selected:
        session.toggle(position)
    assert session.can_shift(-1) is backward
    assert session.can_shift(1) is forward


def test_shift_that_changes_nothing_adds_no_undo_step():
    session = PageSession(2)
    session.toggle(0)
    session.shift(-1)
    assert not session.can_undo


@pytest.mark.parametrize(
    ("selected", "position", "expected", "selection"),
    [
        ([0], 3, [2, 3, 1, 4], {2}),
        ([3], 1, [4, 1, 2, 3], {0}),
        ([0, 2], 2, [2, 1, 3, 4], {1, 2}),  # el bloque empieza en la posición N
        ([0, 2], 3, [2, 4, 1, 3], {2, 3}),  # último inicio posible
    ],
)
def test_move_to_position(selected, position, expected, selection):
    session = PageSession(4)
    for index in selected:
        session.toggle(index)
    session.move_to_position(position)
    assert _pages(session) == expected
    assert session.selection == selection


@pytest.mark.parametrize("position", [0, 4])
def test_move_to_position_out_of_range(position):
    session = PageSession(4)
    session.toggle(0)
    session.toggle(1)
    with pytest.raises(UserError):
        session.move_to_position(position)
    assert session.is_identity


def test_reverse_selection_follows():
    session = PageSession(3)
    session.toggle(0)
    session.reverse()
    assert _pages(session) == [3, 2, 1]
    assert session.selection == {2}


def test_duplicate_keeps_selection_on_originals():
    session = PageSession(3)
    session.toggle(0)
    session.toggle(2)
    session.duplicate()
    assert _pages(session) == [1, 1, 2, 3, 3]
    assert session.selection == {0, 3}


def test_delete_clears_selection():
    session = PageSession(3)
    session.toggle(1)
    session.delete()
    assert _pages(session) == [1, 3]
    assert session.selection == set()


def test_delete_everything_is_refused_and_keeps_state():
    session = PageSession(2)
    session.cycle_all()
    with pytest.raises(UserError):
        session.delete()
    assert _pages(session) == [1, 2]
    assert session.selection == {0, 1}
    assert not session.can_undo


def test_extract_plan_does_not_change_the_session():
    session = PageSession(3)
    session.toggle(2)
    session.toggle(0)
    assert session.extract_plan() == [(1, 0), (3, 0)]
    assert _pages(session) == [1, 2, 3]


@pytest.mark.parametrize(
    ("source", "target", "expected", "selection"),
    [
        (0, 3, [2, 3, 4, 1], {3}),  # hasta la última posición de una vez
        (3, 0, [4, 1, 2, 3], {0}),
        (0, 1, [2, 1, 3, 4], {1}),
        (2, 1, [1, 3, 2, 4], {1}),
    ],
)
def test_drag_takes_the_position_of_the_target(source, target, expected, selection):
    session = PageSession(4)
    session.toggle(source)
    session.drag(source, target)
    assert _pages(session) == expected
    assert session.selection == selection


def test_drag_moves_only_that_page_and_others_stay_selected():
    session = PageSession(4)
    session.toggle(1)
    session.drag(0, 3)
    assert _pages(session) == [2, 3, 4, 1]
    assert session.selection == {0}


def test_drag_onto_itself_is_nothing():
    session = PageSession(3)
    session.drag(1, 1)
    assert not session.can_undo


def test_undo_stack_is_bounded():
    session = PageSession(2)
    session.cycle_all()
    for _ in range(150):
        session.rotate(90)
    undone = 0
    while session.can_undo:
        session.undo()
        undone += 1
    assert undone == 100
