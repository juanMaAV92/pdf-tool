from pdftool.core.config import Settings, load_settings, save_settings


def test_defaults():
    settings = Settings()
    assert settings.theme_mode == "system"


def test_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(theme_mode="dark"), path)

    assert load_settings(path).theme_mode == "dark"


def test_load_corrupt_json_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{no es json", encoding="utf-8")

    assert load_settings(path) == Settings()


def test_load_missing_returns_defaults(tmp_path):
    assert load_settings(tmp_path / "missing.json").theme_mode == "system"


def test_settings_output_dir_defaults_to_none():
    assert Settings().output_dir is None


def test_settings_output_dir_round_trips(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(theme_mode="dark", output_dir="/Users/x/Desktop"), path)

    loaded = load_settings(path)
    assert loaded.output_dir == "/Users/x/Desktop"
    assert loaded.theme_mode == "dark"


def test_settings_none_output_dir_round_trips(tmp_path):
    path = tmp_path / "settings.json"
    save_settings(Settings(), path)

    assert load_settings(path).output_dir is None


def test_load_invalid_theme_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme_mode":"sepia"}', encoding="utf-8")

    assert load_settings(path) == Settings()
