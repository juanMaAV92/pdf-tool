"""Búsqueda de textos: idioma activo, respaldo en inglés, plurales y números."""

import json
from pathlib import Path

import pytest

from pdftool import i18n


def _write(folder: Path, code: str, data: dict | str) -> None:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    (folder / f"{code}.json").write_text(text, encoding="utf-8")


@pytest.fixture
def locales(tmp_path):
    _write(
        tmp_path,
        "en",
        {
            "_meta": {"name": "English", "decimal_separator": "."},
            "a": "A in English",
            "files": {"one": "{count} file", "other": "{count} files"},
            "greet": "Hello {name}",
        },
    )
    _write(
        tmp_path,
        "es",
        {
            "_meta": {"name": "Español", "decimal_separator": ","},
            "a": "A en español",
            "files": {"one": "{count} archivo", "other": "{count} archivos"},
            "greet": "Hola {name}",
        },
    )
    i18n.use_locales_dir(tmp_path)
    yield tmp_path
    i18n.use_locales_dir(None)


def test_t_returns_active_language_and_falls_back_to_english(locales):
    _write(locales, "xx", {"_meta": {"name": "Xx"}, "greet": "Xx {name}"})
    i18n.set_language("es")
    assert i18n.t("a") == "A en español"
    i18n.set_language("xx")
    assert i18n.t("greet", name="Ana") == "Xx Ana"
    assert i18n.t("a") == "A in English"


def test_t_unknown_key_returns_the_key(locales):
    assert i18n.t("nope.key") == "nope.key"


def test_plural_one_and_other(locales):
    i18n.set_language("en")
    assert i18n.t("files", count=1) == "1 file"
    assert i18n.t("files", count=3) == "3 files"
    assert i18n.t("files") == "{count} files"


def test_bad_placeholders_never_raise(locales):
    _write(locales, "xx", {"_meta": {"name": "Xx"}, "greet": "Xx {missing}"})
    i18n.set_language("xx")
    assert i18n.t("greet", name="Ana") == "Hello Ana"
    # Si el inglés tampoco puede formatearse, la plantilla tal cual.
    assert i18n.t("greet") == "Xx {missing}"


def test_broken_locale_file_is_ignored(locales):
    _write(locales, "zz", "{ not json")
    _write(locales, "yy", {"a": "sin meta"})
    codes = [code for code, _ in i18n.available_languages()]
    assert codes == ["en", "es"]


def test_available_languages_lists_new_file(locales):
    _write(locales, "xx", {"_meta": {"name": "Xx"}})
    assert ("xx", "Xx") in i18n.available_languages()


def test_set_language_unknown_falls_back_to_english(locales):
    i18n.set_language("de")
    assert i18n.current_language() == "en"


def test_resolve_language(locales, monkeypatch):
    monkeypatch.setattr(i18n, "_ui_language", lambda: "es-ES")
    assert i18n.resolve_language("es") == "es"
    assert i18n.resolve_language("de") == "es"
    assert i18n.resolve_language("system") == "es"


@pytest.mark.parametrize(
    ("raw", "expected"), [("es-CO", "es"), ("es_ES.UTF-8", "es"), ("de_DE", "en")]
)
def test_system_language_reads_ui_language(locales, monkeypatch, raw, expected):
    monkeypatch.setattr(i18n, "_ui_language", lambda: raw)
    assert i18n.system_language() == expected


def test_system_language_detector_failure_is_english(locales, monkeypatch):
    def boom():
        raise OSError("no locale")

    monkeypatch.setattr(i18n, "_ui_language", boom)
    assert i18n.system_language() == "en"


def test_fmt_number(locales):
    i18n.set_language("es")
    assert i18n.fmt_number(2.5, 2) == "2,50"
    i18n.set_language("en")
    assert i18n.fmt_number(2.5, 2) == "2.50"


def test_attribute_or_index_placeholders_never_raise(locales):
    _write(
        locales, "xx", {"_meta": {"name": "Xx"}, "greet": "Xx {name.nope} {name[0]}"}
    )
    i18n.set_language("xx")
    assert i18n.t("greet", name=5) == "Hello 5"
