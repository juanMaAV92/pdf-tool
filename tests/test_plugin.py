"""El repo es un plugin de Claude Code: manifiestos y skill coherentes con la CLI."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/juanMaAV92/pdf-tool"


def _json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_plugin_manifest_is_valid():
    plugin = _json(".claude-plugin/plugin.json")
    assert plugin["name"] == "pdf-tool"
    assert plugin["description"].strip()
    assert plugin["license"] == "MIT"
    assert plugin["repository"] == REPO_URL
    # Sin versión: el plugin sigue a `main`.
    assert "version" not in plugin


def test_marketplace_lists_this_repo_as_the_plugin():
    market = _json(".claude-plugin/marketplace.json")
    plugin = _json(".claude-plugin/plugin.json")
    assert market["name"] == "pdf-tool"
    assert market["owner"]["name"].strip()
    assert len(market["plugins"]) == 1
    entry = market["plugins"][0]
    assert entry["name"] == plugin["name"]
    assert entry["source"] == "./"


# ---------------------------------------------------------------------------
# La skill: coherente con la CLI real
# ---------------------------------------------------------------------------

SKILL = ROOT / "skills" / "pdf-tool" / "SKILL.md"


def _skill() -> tuple[dict, str]:
    """Frontmatter (`clave: valor` entre `---`) y cuerpo de la skill."""
    text = SKILL.read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = {}
    for line in front.strip().splitlines():
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, body


def _commands(body: str) -> list[list[str]]:
    """Comandos `pdf-tool …` de los bloques de código (sin lo previo a un `|`)."""
    import shlex

    commands, in_block = [], False
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            continue
        line = line.split("|")[-1].strip() if "|" in line else line
        if line.startswith("pdf-tool "):
            commands.append(shlex.split(line.split(" #")[0]))
    return commands


def _tool_ids() -> list[str]:
    from pdftool.core import registry

    registry.discover()
    # Solo las herramientas reales: otros tests registran herramientas falsas
    # en el registro global y pueden seguir ahí según el orden de ejecución.
    return [
        spec.meta.id
        for spec in registry.get_specs()
        if spec.run.__module__.startswith("pdftool.tools.")
    ]


def test_skill_frontmatter():
    meta, _ = _skill()
    assert meta["name"] == "pdf-tool"
    description = meta["description"].lower()
    for word in ("merge", "split", "compress", "password"):
        assert word in description
    # Leer o resumir un PDF no es su caso.
    assert "summar" in description
    # Compite con skills genéricas de PDF: debe pedir que se la prefiera.
    assert "prefer" in description


def test_skill_covers_every_registered_tool():
    _, body = _skill()
    used = {cmd[1] for cmd in _commands(body) if len(cmd) > 1}
    for tool in _tool_ids():
        assert f"`pdf-tool {tool}`" in body or tool in used, tool


def _cli_options(tool: str) -> dict[str, list[str] | None]:
    """Opciones exactas del subcomando y sus valores permitidos (si los hay)."""
    from pdftool.cli import _build_parser
    from pdftool.core import registry

    registry.discover()
    parser = _build_parser(registry.get_specs())
    subparsers = next(a for a in parser._actions if a.choices and tool in a.choices)
    sub = subparsers.choices[tool]
    return {
        opt: (list(a.choices) if a.choices else None)
        for a in sub._actions
        for opt in a.option_strings
    }


def test_skill_flags_exist_in_the_cli():
    """Coincidencia exacta: `--out` no vale aunque exista `--output-dir`."""
    _, body = _skill()
    tools = set(_tool_ids())
    checked = 0
    for cmd in _commands(body):
        if len(cmd) < 2 or cmd[1] not in tools:
            continue
        options = _cli_options(cmd[1])
        for i, token in enumerate(cmd[2:], start=2):
            if not token.startswith("--"):
                continue
            assert token in options, f"{cmd[1]}: {token}"
            choices = options[token]
            if choices is not None:
                assert cmd[i + 1] in choices, f"{cmd[1]} {token} {cmd[i + 1]}"
            checked += 1
    assert checked > 0


def test_output_dir_works_on_every_tool_and_the_skill_shows_it():
    # La skill dice que `--output-dir` vale en todas: comprobarlo y que haya
    # al menos un ejemplo real (los ejemplos sí se validan contra la CLI).
    for tool in _tool_ids():
        assert "--output-dir" in _cli_options(tool), tool
    _, body = _skill()
    assert any("--output-dir" in cmd for cmd in _commands(body))


def test_skill_describes_the_cli_error_json():
    from pdftool.cli.report import error_to_dict

    error = error_to_dict("split", FileNotFoundError("x"))
    _, body = _skill()
    for key in error:
        assert f'"{key}"' in body, key
    for key in error["error"]:
        assert f'"{key}"' in body, key


def test_skill_exit_codes_match_the_cli():
    from pdftool.cli import EXIT_ERROR, EXIT_USAGE
    from pdftool.cli.report import EXIT_PARTIAL

    _, body = _skill()
    for code in (0, EXIT_ERROR, EXIT_USAGE, EXIT_PARTIAL):
        assert f"`{code}`" in body, code


def test_skill_passes_passwords_only_through_stdin():
    _, body = _skill()
    protect = [cmd for cmd in _commands(body) if "protect" in cmd]
    assert protect
    for cmd in protect:
        assert "--password-stdin" in cmd
    assert "--password " not in body
    assert "PDFTOOL_PASSWORD=" not in body
    # Una comilla simple en la contraseña rompería `printf '%s' '...'`.
    assert "'\\''" in body


def test_skill_tells_claude_to_answer_in_the_user_language():
    _, body = _skill()
    assert "language" in body.lower()
    assert "Spanish" in body


def test_skill_install_and_upgrade_commands():
    _, body = _skill()
    for text in (
        "pipx install pdf-tool-cli",
        "uv tool install pdf-tool-cli",
        "pipx upgrade pdf-tool-cli",
        "https://pypi.org/pypi/pdf-tool-cli/json",
        f"{REPO_URL}/issues",
    ):
        assert text in body, text
    assert "pdf-tool-cli[gui]" not in body
