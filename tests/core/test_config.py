from pdftool.core.config import Settings, load_settings, save_settings


def test_defaults():
    s = Settings()
    assert s.theme_mode == "system"


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


def test_one_invalid_field_does_not_discard_the_others(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme_mode":"sepia","output_dir":"/salida"}', encoding="utf-8")

    loaded = load_settings(path)

    assert loaded.theme_mode == "system"
    assert loaded.output_dir == "/salida"


def test_corrupt_file_is_backed_up_before_it_is_replaced(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{no es json", encoding="utf-8")

    assert load_settings(path) == Settings()
    assert (tmp_path / "settings.json.bak").read_text(encoding="utf-8") == "{no es json"


def test_saved_settings_carry_a_schema_version(tmp_path):
    import json

    path = tmp_path / "settings.json"
    save_settings(Settings(), path)
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_files_from_before_versioning_still_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme_mode":"dark"}', encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.theme_mode == "dark"
    assert loaded.schema_version == 1


def test_tools_have_their_own_settings_space(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings()
    settings.tool("compress")["target_mb"] = 2.5
    save_settings(settings, path)

    loaded = load_settings(path)

    assert loaded.tool("compress") == {"target_mb": 2.5}
    assert loaded.tool("merge") == {}
