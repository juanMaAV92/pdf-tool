import tomllib
from pathlib import Path

from flet_cli.utils.project_dependencies import get_poetry_dependencies

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def test_flet_build_bundles_flet_even_though_it_is_optional():
    # `flet build` arma el bundle con [tool.poetry.dependencies] e ignora
    # `optional`. Si Flet se mueve a otra tabla (p. ej. [project]), la app
    # empaquetada se quedaría sin Flet.
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["tool"]["poetry"]["dependencies"]
    assert deps["flet"]["optional"] is True
    assert "flet==0.28.2" in get_poetry_dependencies(deps)


def test_windows_installer_speaks_english_and_spanish():
    """El instalador elige su idioma como la app: según el del sistema."""
    iss = (ROOT / "installer" / "windows.iss").read_text(encoding="utf-8")
    assert 'Name: "english"; MessagesFile: "compiler:Default.isl"' in iss
    assert 'Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"' in iss
    # Solo pregunta el idioma si el del sistema no está entre los disponibles.
    assert "ShowLanguageDialog=auto" in iss
    # Textos propios del instalador por idioma, no escritos en una sola lengua.
    assert 'Description: "{cm:OpenApp}"' in iss
    assert "english.OpenApp=" in iss and "spanish.OpenApp=" in iss


def test_package_summary_is_in_english():
    # Es el resumen de PyPI, encima del README (en inglés).
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    summary = meta["tool"]["poetry"]["description"]
    assert "PDF tools" in summary
    assert not set(summary) & set("áéíóúñ¿¡…")
