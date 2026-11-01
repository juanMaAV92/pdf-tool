# CLAUDE.md

Project guide for Claude Code.

**The source of truth is [AGENTS.md](./AGENTS.md)** — read it first: it covers the architecture, the commands, how to add a tool, the conventions and the packaging.

## Key reminders (summary)

- **Commands:** `poetry install --all-extras` · `poetry run pdftool` · `poetry run pytest`. Never activate venvs by hand; use `poetry run`.
- **Architecture:** `core/` without Flet; each tool separates `logic.py` (pure, testable) from `panel.py` (UI). `inputs` is always `list[Path]`; the output path is decided by `core/naming.py` (chosen destination or next to the original, never overwriting) — never composed by hand.
- **TDD:** failing test → implementation, on the pure logic.
- **Flet 0.28.x:** `ft.Icons.*` / `ft.Colors.*` (capitalized enums).
- **Commits:** plain messages, Conventional Commits. **Never** add `Co-Authored-By: Claude`, "Generated with Claude Code" or any AI attribution.
- **Adding a tool:** `params.py` + `logic.py` + `spec.py` (no Flet, registers the `ToolSpec`) + `panel.py` with `@register` and `spec = SPEC`; empty `__init__.py`. The host is not touched; every spec needs a panel (app and CLI in step), its example in `skills/pdf-tool/SKILL.md` and its texts in `pdftool/i18n/locales/en.json` and `es.json` (no visible text in the code).
- **Language:** talk to the user in the language they use; contributor docs are in English, `docs/roadmap.md` in Spanish.
