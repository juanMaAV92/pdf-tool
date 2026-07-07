from pdftool.ui.errors import humanize_error


def test_value_error_passes_through():
    msg, detail = humanize_error(ValueError("Contraseña incorrecta."))
    assert msg == "Contraseña incorrecta."
    assert detail is None


def test_file_not_found_is_friendly():
    msg, detail = humanize_error(FileNotFoundError("/tmp/x.pdf"))
    assert "No se encontró el archivo" in msg
    assert detail is None


def test_permission_error_is_friendly():
    msg, detail = humanize_error(PermissionError("denied"))
    assert "No se pudo guardar" in msg
    assert detail is None


def test_unexpected_error_is_generic_with_detail():
    msg, detail = humanize_error(RuntimeError("cannot open broken document"))
    assert msg == "No se pudo procesar el PDF. Puede estar dañado o protegido."
    assert detail == "RuntimeError: cannot open broken document"
