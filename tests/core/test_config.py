from pdftool.core.config import Settings, load_settings, save_settings


def test_defaults():
    s = Settings()
    assert s.theme_mode == "system"


def test_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(theme_mode="dark"), path)
    loaded = load_settings(path)
    assert loaded.theme_mode == "dark"


def test_load_missing_returns_defaults(tmp_path):
    loaded = load_settings(tmp_path / "missing.json")
    assert loaded.theme_mode == "system"
