from pathlib import Path

from pdftool.core.config import Settings, load_settings
from pdftool.ui.output_dir import OutputDirField, abbreviate_home


def test_abbreviate_home_uses_tilde():
    assert abbreviate_home(Path.home() / "Desktop") == "~/Desktop"


def test_abbreviate_home_leaves_other_paths_alone():
    assert abbreviate_home(Path("/tmp/x")) == "/tmp/x"


def test_default_is_next_to_the_original():
    field = OutputDirField(Settings())
    assert field.value is None
    assert field.label.value == "Junto al original"
    assert field.reset_btn.visible is False


def test_a_persisted_folder_is_restored(tmp_path):
    field = OutputDirField(Settings(output_dir=str(tmp_path)))
    assert field.value == tmp_path
    assert field.label.value == abbreviate_home(tmp_path)
    assert field.reset_btn.visible is True


def test_a_persisted_folder_that_vanished_falls_back_to_the_default(tmp_path):
    """Disco desconectado o carpeta borrada: se vuelve al default sin ruido."""
    settings = Settings(output_dir=str(tmp_path / "no-existe"))
    field = OutputDirField(settings, settings_path=tmp_path / "settings.json")
    assert field.value is None
    assert field.label.value == "Junto al original"
    assert settings.output_dir is None


def test_choosing_a_folder_updates_state_and_settings(tmp_path):
    settings = Settings()
    field = OutputDirField(settings, settings_path=tmp_path / "settings.json")

    field.set_dir(tmp_path)

    assert field.value == tmp_path
    assert settings.output_dir == str(tmp_path)
    assert field.reset_btn.visible is True


def test_the_choice_is_written_to_disk(tmp_path):
    """Se persiste al cambiar, no al ejecutar."""
    path = tmp_path / "settings.json"
    OutputDirField(Settings(), settings_path=path).set_dir(tmp_path)
    assert load_settings(path).output_dir == str(tmp_path)


def test_reset_returns_to_the_default(tmp_path):
    settings = Settings(output_dir=str(tmp_path))
    field = OutputDirField(settings, settings_path=tmp_path / "settings.json")

    field.set_dir(None)

    assert field.value is None
    assert settings.output_dir is None
    assert field.label.value == "Junto al original"
    assert field.reset_btn.visible is False


def test_on_change_fires_when_the_destination_changes(tmp_path):
    seen = []
    field = OutputDirField(Settings(), on_change=lambda: seen.append(1),
                           settings_path=tmp_path / "settings.json")

    field.set_dir(tmp_path)
    field.set_dir(None)

    assert len(seen) == 2
