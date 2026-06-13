import pytest
from pydantic import ValidationError
from pdftool.tools.compress.params import CompressParams


def test_default_target_is_5mb():
    assert CompressParams().target_mb == 5.0


def test_target_must_be_positive():
    with pytest.raises(ValidationError):
        CompressParams(target_mb=0)
