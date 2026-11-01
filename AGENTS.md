# AGENTS.md

Guide for coding agents (Claude Code, etc.) working on **pdf-tool**.

## What it is

A **modular** desktop app (Flet) for managing PDFs, designed for **non-technical** users, plus a CLI (`pdf-tool`) for agents generated from the same tools. Cross-platform (macOS + Windows), installable and self-updating. Each feature is a self-contained "tool" that the host discovers and shows. It currently includes Compress, Images to PDF, Merge, Protect, Split and Watermark.

## Commands

```bash
poetry install --all-extras   # install dependencies (with Flet, the [gui] extra)
poetry run pdftool      # open the desktop app
poetry run pdf-tool list            # CLI: available tools (--json for agents)
poetry run pdf-tool compress a.pdf --json   # CLI: run a tool
poetry run pytest       # run the test suite
poetry run pytest -v    # tests with detail
poetry run ruff format pdftool tests && poetry run ruff check pdftool tests && poetry run mypy
                        # same as CI requires (mypy checks the whole package)
pipx install pre-commit && pre-commit install   # optional: the above on every commit
```

> **Do not activate venvs by hand** (`source .../activate`). Always use `poetry run`; Poetry manages the project environment. Activating another venv causes `[Errno 2] ... 'python'` when launching Flet.

## Architecture

```
pdftool/
├── main.py                 # entrypoint -> ft.app(target=build_app)
├── i18n/                   # NO Flet: t(), active language; locales/<code>.json (one dictionary per language)
├── cli/                    # `pdf-tool`, NO Flet: subcommands from the spec registry
│   ├── __init__.py         # main(): list, <tool>, --json, --lang, exit codes 0/1/2/3
│   ├── args.py             # Pydantic params -> argparse flags (secrets via stdin/env)
│   └── report.py           # ToolResult -> text or JSON
├── core/                   # NO Flet dependency (testable in isolation)
│   ├── plugin.py           # contract: ToolMeta, ToolSpec, ToolResult, ToolContext, Progress, PdfTool
│   ├── registry.py         # specs without Flet: register(), get_specs(), discover() (app and CLI)
│   ├── jobs.py             # run_job(...) with JobHandle, cancellation and generations
│   ├── atomic.py           # atomic publishing of PDFs and copies
│   ├── batch.py            # run_batch(): shared batch loop (per-file errors)
│   ├── config.py           # versioned Settings; settings.tool(id) for per-tool preferences
│   ├── errors.py           # UserError and user_message(): messages for the user
│   ├── logger.py           # rotating log with redacted paths and names
│   ├── naming.py           # destinations, name collisions, localized suffixes
│   ├── thumbnails.py       # pure thumbnail rendering
│   └── updater.py          # GITHUB_REPO, check_for_update() via GitHub Releases (never raises)
├── ui/
│   ├── app.py              # host: sidebar + content + footer menu (theme, language) + update banner
│   ├── panel_base.py       # BaseToolPanel / SingleFileToolPanel: panel template
│   ├── registry.py         # panels: @register, get_tools(), discover()
│   ├── file_list.py        # MultiFileToolPanel: batch list, results, thumbnails
│   ├── output_dir.py       # «Save to» field (persisted in Settings)
│   ├── errors.py           # humanize_error() for the UI (delegates to core/errors)
│   ├── accessibility.py    # NamedIconButton, HelpButton
│   ├── thumbnails.py       # parallel loading per (path, page), cache by mtime
│   ├── logs.py             # «Save diagnostic report»
│   ├── platform.py         # open file / folder in the OS
│   └── theme.py            # build_theme(), resolve_mode(), next_mode()
└── tools/
    ├── compress/
    ├── images2pdf/
    ├── merge/
    ├── protect/
    ├── split/
    └── watermark/          # each folder: params.py, logic.py, spec.py, panel.py and an empty __init__.py
```

**Golden rule:** `core/` does not import Flet. Each tool's logic (`logic.py`) is **pure** (no Flet) and tested on its own; its `spec.py` publishes it without Flet for the app and the CLI; `panel.py` only builds the UI and delegates to the spec.

## How to add a new tool

The host is not touched. Create `pdftool/tools/<id>/` with:

1. `params.py` — inherits from `BaseParams` (`pdftool/core/plugin.py`), not
   plain `BaseModel`: `BaseParams` provides `output_dir`, and a tool that does
   not inherit it will silently ignore the output folder the user chose.
   Field help does not go in `Field(description=...)` but in the
   dictionaries: `tool.<id>.param.<field>` and, for each value of a `Literal`,
   `tool.<id>.param.<field>.<value>` (a test requires it). A secret (password)
   carries `json_schema_extra={"secret": True}` and the CLI only accepts it via
   stdin or an environment variable. Validation lives in the model
   (`field_validator`), not in the panel, so the app and the CLI share it.
2. `logic.py` — pure function with the uniform signature:
   ```python
   def run(inputs: list[Path], params: <Params>, progress: Progress = _noop) -> ToolResult: ...
   ```
   `inputs` is **always** `list[Path]` (1→1, N→1, 1→N). The output path is
   **never composed by hand**: ask `pdftool/core/naming.py`, which resolves the
   destination and collisions in one place.
   ```python
   # automatic name «<stem>_<suffix>.pdf» (the suffix follows the language)
   out = output_path(input_path, localized_suffix("tool.<id>.suffix"), out_dir=params.output_dir)
   # free name (Merge, Images to PDF)
   out = unique_path((params.output_dir or input_path.parent) / f"{base}.pdf")
   ```
   With `output_dir=None` the output goes next to the original, which is the
   default. No tool may overwrite an existing file: `unique_path` adds
   « (1)», « (2)»… and is the single source of that rule.

   **Batches (N→N):** do not write the loop by hand; use
   `run_batch(inputs, process_one, progress, all_failed=...)` from
   `pdftool/core/batch.py`. It isolates each file's failure in its
   `FileResult`, scales the progress (`[i/N] name: …`) and lets cancellation
   through. `process_one` can return `(output, message)` or an `Outcome` with
   `warnings` and `metrics` when the user must know something about the result
   (e.g. «pages were rasterized»; sizes and % saved). The UI shows warnings
   under the summary and in the file's row, without dialogs.

   **Errors for the user:** raise `UserError(t("tool.<id>.error.…"))`
   (`pdftool/core/errors.py`) when the message must be shown as is. Any other
   exception is shown as a generic message with the detail folded away.
3. `spec.py` — **no Flet**. Declares and registers the tool for the app and the
   CLI:
   ```python
   SPEC = register(ToolSpec(meta=ToolMeta(id=..., category=..., order=...),
                            params=<Params>, run=<function from logic.py>,
                            min_inputs=1, max_inputs=None, extensions=("pdf",)))
   ```
   (`register` from `pdftool/core/registry.py`; `order` sets its position in the
   navigation). The name and description come from `tool.<id>.name` and
   `tool.<id>.description`; `category` is an id (`organize`, `optimize`,
   `convert`, `edit`, `security`) with its text in `category.<id>`. The input
   rules apply to the app (the panel inherits them) and to the CLI. The CLI is
   not touched: the tool appears on its own in `pdf-tool list`.
4. `panel.py` — class decorated with `@register` (`pdftool/ui/registry.py`) that
   inherits the UI template: `MultiFileToolPanel` (`pdftool/ui/file_list.py`)
   for batches or `SingleFileToolPanel` (`pdftool/ui/panel_base.py`) for a
   single file. Declare `spec = SPEC` (that is where `meta` and the logic come
   from), `icon = ft.Icons.*`, `run_label_key`/`run_icon`/`pick_label_key`
   (dictionary keys) and implement the `extra_controls()` and `make_params()`
   hooks. `make_params()` raises `InvalidParams("message", field=field)` to
   also mark the error on the field. In batches, `reorderable = True` only if
   the order changes the result (as in Merge).

   The base builds the panel **once per page** and reuses it when coming back
   to the tool: the list, the fields, the result and the running job are kept.
   It also runs the logic in the background with `ctx.run_job` (with a Cancel
   button); do not call it yourself except for the panel's own reads (e.g.
   Split reads the page count that way, never on the UI thread).
5. `__init__.py` — empty. Discovery imports `spec.py` (core) and `panel.py`
   (UI) on its own.

**App and CLI in step:** every spec needs its panel and vice versa;
`tests/ui/test_registry.py::test_every_spec_has_a_panel_and_vice_versa`
requires it. And `tests/core/test_no_flet.py` checks that specs are discovered
without Flet.

**Languages:** no visible text is written in the code: everything comes from
`pdftool/i18n/locales/<code>.json` via `t("key", **data)` (plurals with
`{"one": …, "other": …}` and `count`). `en.json` is the reference and the
fallback; `en.json` and `es.json` must always have the same keys. A new tool
adds its keys to both. `tests/i18n/test_no_hardcoded_text.py` fails if a
sentence is left in a literal; the log and the technical detail are not
translated. **Adding a language:** copy `en.json` to `<code>.json`, change
`_meta.name` (its name in that language) and `_meta.decimal_separator`, and
translate; it appears on its own in the app menu and in `--lang`. Anything
missing falls back to English.

**Agent skill:** `skills/pdf-tool/SKILL.md` (in English, open Agent Skills
format, nothing specific to one agent) teaches how to use the CLI. It installs
as a Claude Code plugin (`.claude-plugin/`), with
`npx skills add juanMaAV92/pdf-tool`, or by copying the folder. When adding a
tool, mention it in the skill with an example: `tests/test_plugin.py` fails if
it is missing, or if the skill cites flags or exit codes the CLI does not have.

`discover()` finds it automatically and it appears in the sidebar, in its
`meta.category` group (the sidebar scrolls, so many fit). If a tool fails to
import, it is logged and the rest of the app keeps working; two tools with the
same `meta.id` are an error.

## Conventions

- **TDD:** first the failing test (on the pure logic), then the implementation. Panels have state tests; full visual validation is still manual.
- **Pure logic tests** live in `tests/` mirroring the structure. PDF fixtures in `tests/conftest.py`. Tests run in Spanish by default (autouse fixture); tests that need another language set it explicitly.
- **Flet 0.28.x:** icons and colors are **capitalized** enums (`ft.Icons.*`, `ft.Colors.*`). Window size: `page.window.width/height`. Opening a banner: `page.open(banner)`.
- Heavy operations **always** run in the background via `run_job` so the UI does not freeze.
- Documentation for contributors is in English; `docs/roadmap.md` stays in Spanish.

## Commits

- **DO NOT** add co-authorship trailers or AI attribution: no `Co-Authored-By: Claude`, no `Generated with Claude Code`, nothing similar. Plain messages.
- Conventional Commits style: `feat(...)`, `fix(...)`, `chore(...)`, `docs(...)`.
- Do not commit during implementation without review unless asked; the repo flow uses PRs against `main`.

## Packaging and distribution

- macOS: `poetry run flet build macos --project pdf-tool --product pdf-tool` → `.app` → wrap in a `.dmg`.
- Windows: `poetry run flet build windows --project pdf-tool --product pdf-tool` → compile `installer/windows.iss` with Inno Setup → `pdf-tool-setup.exe` (updates in place, same `AppId`; English and Spanish, chosen from the system language).
- **PyPI** (`pdf-tool-cli`, because `pdf-tool` clashes with the existing `pdftool`): `pip install pdf-tool-cli` brings only the CLI (command `pdf-tool`); Flet is the `[gui]` extra (command `pdftool`, which explains how to install Flet if it is missing). Flet stays in `[tool.poetry.dependencies]` (optional) and not in `[project]`, because `flet build` reads that table and ignores `optional`: that way the bundle keeps Flet. Do not migrate to `[project]` without checking that. `flet build` also takes the bundle's internal name from `tool.poetry.name`: that is why the workflows pass `--project "pdf-tool"` (changing it would break the identity of the installed app). The CI `cli-wheel` job installs the wheel without extras and tests the CLI (including `--lang en` and `--lang es`).
- The release workflow publishes to PyPI with Trusted Publishing (job `publish-pypi`, environment `pypi`) after building the DMG and installer, because a version uploaded to PyPI cannot be replaced.
- Distribution via **GitHub Releases** with a `vX.Y.Z` tag. The release workflow takes the version from the tag; the repo used by the update check is in `GITHUB_REPO` (`core/updater.py`).
- **To release:** `git tag vX.Y.Z && git push origin vX.Y.Z`. `release.yml` runs the tests, builds macOS and Windows in parallel and creates a **draft GitHub Release** with both installers. Review it and click **Publish release** so installed apps detect the update. The PyPI step waits for approval in Actions (`pypi` environment). The tag is the only source of the version number.
- PRs that change the app, the packaging or its dependencies also run **Package smoke**, which builds the macOS DMG and silently installs the Windows installer. Before a major release, follow the manual checklist in `docs/release-smoke.md`.
- Published PyPI descriptions are frozen and load their images from `main`: do not rename or delete files in `docs/` that a published README references (such as `docs/screenshot.png`).
- The release publishes `SHA256SUMS.txt` and a provenance attestation (`gh attestation verify`). Actions are pinned by SHA (Dependabot updates them) and Poetry, the export plugin and Inno Setup by version.
- CI runs `pip-audit` on the runtime dependencies. A vulnerability without a compatible fix is ignored explicitly in `ci.yml`, with the reason.
- User settings live outside the binary (`platformdirs`), so they survive updates.

## Notes

- The project uses **Flet 0.28.x**. CI pins **Flutter 3.29.3** (compatible with flet 0.28 and VS 2022) and **Python 3.12** for `flet build`. flet 0.24.1 became obsolete: it did not build for Windows on current runners.
- The current direction is in `docs/roadmap.md` (in Spanish). The Flet 0.28.2 pin is explained in `pyproject.toml`. Temporary specs and plans are not part of the repository and are not kept once the feature is implemented.
