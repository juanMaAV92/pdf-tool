"""Los diccionarios reales: inglés y español completos y coherentes."""

import json
import string

from pdftool.i18n import LOCALES_DIR


def _all() -> dict[str, dict]:
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(LOCALES_DIR.glob("*.json"))
    }


def _forms(value) -> dict[str, str]:
    return value if isinstance(value, dict) else {"": value}


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_en_and_es_exist():
    assert {"en", "es"} <= set(_all())


def test_en_and_es_have_the_same_keys():
    locales = _all()
    assert set(locales["en"]) == set(locales["es"])


def test_no_locale_has_keys_missing_from_english():
    locales = _all()
    for code, data in locales.items():
        extra = set(data) - set(locales["en"])
        assert not extra, (code, sorted(extra))


def test_placeholders_match_english():
    locales = _all()
    english = locales["en"]
    for code, data in locales.items():
        for key, value in data.items():
            if key == "_meta":
                continue
            reference = {f: _fields(text) for f, text in _forms(english[key]).items()}
            expected = set().union(*reference.values())
            for text in _forms(value).values():
                assert _fields(text) <= expected, (code, key)


def test_plurals_have_one_and_other():
    for code, data in _all().items():
        for key, value in data.items():
            if key != "_meta" and isinstance(value, dict):
                assert set(value) == {"one", "other"}, (code, key)
