import tomllib
from pathlib import Path

from flet_cli.utils.project_dependencies import get_poetry_dependencies

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def test_flet_build_bundles_flet_even_though_it_is_optional():
    # `flet build` arma el bundle con [tool.poetry.dependencies] e ignora
    # `optional`. Si Flet se mueve a otra tabla (p. ej. [project]), la app
    # empaquetada se quedaría sin Flet.
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = data["tool"]["poetry"]["dependencies"]
    assert deps["flet"]["optional"] is True
    assert "flet==0.28.2" in get_poetry_dependencies(deps)
