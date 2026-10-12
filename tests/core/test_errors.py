from pdftool.core.errors import UserError, user_message


def test_user_error_is_shown_verbatim():
    assert user_message(UserError("Contraseña incorrecta.")) == (
        "Contraseña incorrecta.",
        None,
    )


def test_user_error_is_a_value_error():
    assert isinstance(UserError("x"), ValueError)


def test_plain_value_error_is_not_shown_verbatim():
    msg, detail = user_message(ValueError("bad xref table"))
    assert "bad xref" not in msg
    assert detail == "ValueError: bad xref table"


def test_generic_message_suggests_next_step():
    msg, _ = user_message(RuntimeError("cannot open broken document"))
    assert "contraseña" in msg
    assert "Proteger PDF" in msg


def test_permission_error_mentions_choosing_another_folder():
    msg, detail = user_message(PermissionError("denied"))
    assert "Guardar en" in msg
    assert detail is None


def test_file_not_found_is_friendly():
    msg, detail = user_message(FileNotFoundError("/tmp/x.pdf"))
    assert "No se encontró el archivo" in msg
    assert detail is None
