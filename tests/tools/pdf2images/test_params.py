import pytest
from pydantic import ValidationError

from pdftool.tools.pdf2images.params import Pdf2ImagesParams


def test_defaults_are_print_quality_jpg():
    params = Pdf2ImagesParams()
    assert params.format == "jpg"
    assert params.dpi == 300


@pytest.mark.parametrize("dpi", [71, 601])
def test_dpi_out_of_range_is_rejected(dpi):
    with pytest.raises(ValidationError):
        Pdf2ImagesParams(dpi=dpi)


def test_unknown_format_is_rejected():
    with pytest.raises(ValidationError):
        Pdf2ImagesParams(format="tiff")
