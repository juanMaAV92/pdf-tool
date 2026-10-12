from pdftool.core.updater import check_for_update, is_newer


def test_is_newer_true():
    assert is_newer("0.2.0", "0.1.0")


def test_is_newer_false_equal():
    assert not is_newer("0.1.0", "0.1.0")


def test_is_newer_handles_v_prefix():
    assert is_newer("v1.0.0", "0.9.9")


def test_check_for_update_returns_url_when_newer():
    fake = {
        "tag_name": "v0.2.0",
        "html_url": "https://github.com/me/pdf-tool/releases/tag/v0.2.0",
    }
    url = check_for_update(
        current="0.1.0", repo="me/pdf-tool", http_get=lambda _u: fake
    )
    assert url == "https://github.com/me/pdf-tool/releases/tag/v0.2.0"


def test_check_for_update_returns_none_when_current():
    fake = {
        "tag_name": "v0.1.0",
        "html_url": "https://github.com/me/pdf-tool/releases/tag/v0.2.0",
    }
    url = check_for_update(
        current="0.1.0", repo="me/pdf-tool", http_get=lambda _u: fake
    )
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
    fake = {
        "tag_name": "v1.2.0-beta.1",
        "html_url": "https://github.com/me/pdf-tool/releases/tag/v0.2.0",
    }
    url = check_for_update(
        current="1.1.0", repo="me/pdf-tool", http_get=lambda _u: fake
    )
    assert url == "https://github.com/me/pdf-tool/releases/tag/v0.2.0"


def _check(data, repo="me/pdf-tool"):
    return check_for_update(current="0.1.0", repo=repo, http_get=lambda _u: data)


def test_release_url_must_belong_to_the_repo():
    for url in (
        "https://github.com/otro/repo/releases/tag/v9.0.0",
        "http://github.com/me/pdf-tool/releases/tag/v9.0.0",
        "file:///etc/passwd",
        "https://github.com/me/pdf-tool.evil.com/releases/x",
    ):
        assert _check({"tag_name": "v9.0.0", "html_url": url}) is None, url


def test_malformed_tag_is_ignored():
    url = "https://github.com/me/pdf-tool/releases/tag/x"
    assert _check({"tag_name": "9; rm -rf", "html_url": url}) is None


def test_default_repo_is_defined_in_the_core():
    from pdftool.core.updater import GITHUB_REPO

    assert GITHUB_REPO == "juanMaAV92/pdf-tool"


def test_oversized_response_is_rejected(monkeypatch):
    import pdftool.core.updater as updater

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n=-1):
            body = b"x" * (updater._MAX_RESPONSE_BYTES + 10)
            return body if n < 0 else body[:n]

    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: _Resp())
    import pytest

    with pytest.raises(ValueError, match="demasiado grande"):
        updater._default_get("https://api.github.com/x")
