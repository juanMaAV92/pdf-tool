import pytest
from pydantic import ValidationError

from pdftool.tools.split.params import SplitParams


def test_defaults():
    p = SplitParams()
    assert p.mode == "ranges"
    assert p.ranges == ""
    assert p.every_n == 1


def test_every_n_must_be_positive():
    with pytest.raises(ValidationError):
        SplitParams(mode="every", every_n=0)


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        SplitParams(mode="nope")
