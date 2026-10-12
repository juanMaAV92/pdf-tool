from pdftool.core.errors import UserError, user_message
from pdftool.ui.errors import humanize_error


def test_ui_uses_the_core_translation():
    for exc in (UserError("Contraseña incorrecta."), RuntimeError("x")):
        assert humanize_error(exc) == user_message(exc)
