def test_color_components_must_be_between_0_and_1():
    import pytest
    from pydantic import ValidationError

    from pdftool.tools.watermark.params import WatermarkParams

    with pytest.raises(ValidationError):
        WatermarkParams(text="x", color=(2.0, 0.0, 0.0))
