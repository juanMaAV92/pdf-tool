import pytest
from pydantic import ValidationError

from pdftool.tools.merge.params import MergeParams


def test_output_name_is_sanitized():
    assert MergeParams(output_name=" informe.pdf ").output_name == "informe"
    assert MergeParams(output_name="  ").output_name is None
    with pytest.raises(ValidationError):
        MergeParams(output_name="a/b")
