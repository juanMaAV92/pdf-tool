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
