from pdftool.core.updater import is_newer, check_for_update


def test_is_newer_true():
    assert is_newer("0.2.0", "0.1.0")


def test_is_newer_false_equal():
    assert not is_newer("0.1.0", "0.1.0")


def test_is_newer_handles_v_prefix():
    assert is_newer("v1.0.0", "0.9.9")


def test_check_for_update_returns_url_when_newer():
    fake = {"tag_name": "v0.2.0", "html_url": "https://example/release"}
    url = check_for_update(current="0.1.0", repo="me/pdf-tool",
                           http_get=lambda _u: fake)
    assert url == "https://example/release"


def test_check_for_update_returns_none_when_current():
    fake = {"tag_name": "v0.1.0", "html_url": "https://example/release"}
    url = check_for_update(current="0.1.0", repo="me/pdf-tool",
                           http_get=lambda _u: fake)
    assert url is None


def test_check_for_update_swallows_errors():
    def boom(_u):
        raise OSError("offline")

    assert check_for_update(current="0.1.0", repo="me/pdf-tool", http_get=boom) is None


def test_is_newer_handles_prerelease_suffix():
    # Un tag con sufijo (p.ej. una preversión) no debe reventar el parseo.
    assert is_newer("v1.2.0-beta", "1.1.0")
    assert not is_newer("v1.2.0-beta", "1.2.0")


def test_is_newer_normalizes_differing_lengths():
    assert not is_newer("1.2.0", "1.2")
    assert is_newer("1.2.1", "1.2")


def test_check_for_update_survives_prerelease_tag():
    # Antes: _parse reventaba y check_for_update devolvía None en silencio,
    # dejando de avisar de nuevas versiones. Ahora debe detectar la novedad.
    fake = {"tag_name": "v1.2.0-beta.1", "html_url": "https://example/release"}
    url = check_for_update(current="1.1.0", repo="me/pdf-tool",
                           http_get=lambda _u: fake)
    assert url == "https://example/release"
