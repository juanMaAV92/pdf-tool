from pdftool.tools.protect.params import ProtectParams


def test_password_is_marked_secret():
    assert ProtectParams.model_fields["password"].json_schema_extra == {"secret": True}
