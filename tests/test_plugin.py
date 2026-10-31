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
