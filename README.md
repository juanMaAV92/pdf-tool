<div align="center">

# 📄 pdf-tool

**Local PDF tools for the command line, AI agents and the desktop.
Nothing leaves your computer.**

**English** · [Español](https://github.com/juanMaAV92/pdf-tool/blob/main/README.es.md)

[![PyPI](https://img.shields.io/pypi/v/pdf-tool-cli?label=PyPI)](https://pypi.org/project/pdf-tool-cli/)
[![CI](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/juanMaAV92/pdf-tool?label=release)](https://github.com/juanMaAV92/pdf-tool/releases/latest)
[![License](https://img.shields.io/badge/license-MIT_·_AGPL_builds-blue.svg)](#-license)
![Platform](https://img.shields.io/badge/macOS_·_Windows_·_Linux_(CLI)-lightgrey)

</div>

Merge, split, compress, protect and watermark PDFs, or turn images into PDFs,
with a CLI built for scripts and AI agents, an agent skill, and a desktop app
for everyone else. Free, open source, no ads, and **100% offline**: your files
are never uploaded anywhere.

```bash
pipx install pdf-tool-cli
pdf-tool compress report.pdf --target-mb 2
```

---

## 🧰 Tools

| Command | What it does |
|---|---|
| `pdf-tool compress` | Shrinks one or more PDFs to a target size in MB. |
| `pdf-tool merge` | Combines several PDFs into one, in the order you give. |
| `pdf-tool split` | Splits a PDF by page ranges, one page per file, or every N pages. |
| `pdf-tool images2pdf` | Turns each JPG/PNG image into its own PDF. |
| `pdf-tool protect` | Adds or removes the password of one or more PDFs. |
| `pdf-tool watermark` | Repeats a text diagonally across every page. |

It never overwrites your files: outputs go next to the original (or to
`--output-dir`) with a new name.

---

## ⌨️ Command line

```bash
pipx install pdf-tool-cli                      # or: uv tool install pdf-tool-cli
pdf-tool list --json                           # tools, accepted inputs and parameters
pdf-tool compress big.pdf --target-mb 2 --json # result as JSON
pdf-tool compress big.pdf --target-mb 2 --mode preserve   # keep text and links
pdf-tool merge a.pdf b.pdf c.pdf --output-name report
pdf-tool split doc.pdf --ranges "1-3, 5, 8-"
printf '%s' "$PASSWORD" | pdf-tool protect doc.pdf --password-stdin
```

- **Help:** `pdf-tool <tool> --help` lists every flag.
- **JSON for agents:** `--json` prints a stable structure (`ok`, `summary`,
  `outputs`, per-file `items`, `warnings`, `metrics` such as sizes before and
  after compressing).
- **Exit codes:** `0` success · `1` processing failed · `2` invalid usage ·
  `3` batch finished but some files failed.
- **Passwords** are read from stdin (`--password-stdin`) or the
  `PDFTOOL_PASSWORD` variable, never from arguments.
- **Language:** messages and output file names follow your system language;
  `--lang en` or `--lang es` overrides it (or set `PDFTOOL_LANG`).
- **Compression modes:** `max` (default) tries to reduce images first and only
  turns pages into images if that is the only way to reach the target (it warns
  you). `preserve` never does, so text, links and annotations are kept.

Requires Python 3.11+. `pipx install 'pdf-tool-cli[gui]'` also installs the
desktop app (command `pdftool`).

---

## 🤖 Use it with AI agents

A [skill](https://github.com/juanMaAV92/pdf-tool/blob/main/skills/pdf-tool/SKILL.md)
teaches your agent to use `pdf-tool` instead of writing throwaway scripts: it
asks before installing the CLI, runs the tools with `--json` and explains the
result in your language. It follows the open
[Agent Skills](https://agentskills.io) format, so it works with Claude Code,
Codex, Cursor, Gemini CLI, GitHub Copilot and others. Pick **one** way:

**1. Claude Code (plugin, recommended):** updates itself from `main`.

```text
/plugin marketplace add juanMaAV92/pdf-tool
/plugin install pdf-tool@pdf-tool
```

**2. Any agent, with [`skills`](https://github.com/vercel-labs/skills)**
(needs Node.js): detects your agents and copies the skill into each one's
folder. Add `-g` to have it in every project; update it with
`npx skills update`.

```bash
npx skills add juanMaAV92/pdf-tool
```

**3. By hand:** copy the
[`skills/pdf-tool`](https://github.com/juanMaAV92/pdf-tool/tree/main/skills/pdf-tool)
folder into your agent's skills folder
([paths per agent](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)).
Copy it again to update.

In all three, the CLI is installed separately (`pipx install pdf-tool-cli`); if
it is missing, the skill asks for permission to install it.

---

## 🖥️ Desktop app

<img width="980" alt="pdf-tool desktop app: home screen with the six tools" src="https://raw.githubusercontent.com/juanMaAV92/pdf-tool/main/docs/screenshot.png" />

The same six tools with a simple interface, in English or Spanish, for macOS and
Windows. No Python needed.

[![Download](https://img.shields.io/badge/⬇️_Download-latest_version-2ea44f?style=for-the-badge)](https://github.com/juanMaAV92/pdf-tool/releases/latest)

- **macOS:** open the `.dmg` and drag **pdf-tool** to *Applications*. The app is
  not signed, so the first time go to **System Settings → Privacy & Security**
  and click **Open Anyway**.
- **Windows:** run the installer. If SmartScreen appears: **More info → Run
  anyway**.

Step-by-step guide, screenshots and FAQ:
**[juanmaav92.github.io/pdf-tool](https://juanmaav92.github.io/pdf-tool)**.
Every release publishes `SHA256SUMS.txt` so you can check the download.

---

## 🤝 Contributing

Issues and pull requests are welcome. Adding a tool means creating one folder:
the app and the CLI discover it on their own. Translations are welcome too:
copy `pdftool/i18n/locales/en.json` to `<code>.json` and translate it. The
[roadmap](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/roadmap.md)
lists what comes next.

<details>
<summary><b>🛠️ Developer setup</b></summary>

### Requirements
- Python 3.11+ and [Poetry](https://python-poetry.org/)

### Run
```bash
poetry install --all-extras   # includes Flet (the [gui] extra) for the app
poetry run pdftool            # opens the app
poetry run pdf-tool --help    # the CLI
poetry run pytest             # tests
```

### Add a tool
1. Create `pdftool/tools/<id>/` with `params.py`, `logic.py` (pure function +
   tests), `spec.py` (registers the tool, no Flet), `panel.py` and an empty
   `__init__.py`.
2. Add its texts to `pdftool/i18n/locales/en.json` and `es.json`, and an example
   to the skill.
3. The app shows it in the sidebar and the CLI offers it as `pdf-tool <id>`,
   both automatically.

Details in [AGENTS.md](https://github.com/juanMaAV92/pdf-tool/blob/main/AGENTS.md).

### Release (automated with GitHub Actions)
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
`release.yml` runs the tests, builds macOS (`.dmg`) and Windows (Inno Setup
installer) in parallel, bakes the tag version into the build and creates a
**draft GitHub Release** with both installers. Review it and click **Publish
release** so installed apps detect the update. It also publishes the package to
**PyPI** (`pdf-tool-cli`, via Trusted Publishing); that step waits for your
approval in Actions (`pypi` environment), because a PyPI version cannot be
replaced. The tag is the only source of the version number.

PRs that change the app, the packaging or its dependencies also run **Package
smoke**, which builds the macOS DMG and silently installs the Windows installer.
Before a major release, follow the
[manual checklist](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/release-smoke.md).

### Local build (to debug packaging)
```bash
poetry run flet build macos --project pdf-tool --product pdf-tool     # -> build/macos/pdf-tool.app
poetry run flet build windows --project pdf-tool --product pdf-tool   # -> build/windows/
```
`--project pdf-tool` is required: without it, `flet build` takes the package
name (`pdf-tool-cli`) and the app changes identity.

</details>

---

## 📄 License

The pdf-tool source code is [MIT](https://github.com/juanMaAV92/pdf-tool/blob/main/LICENSE).
It uses [PyMuPDF](https://pymupdf.readthedocs.io), licensed under the AGPL, so
the installers and the PyPI package, which include it, are distributed under the
terms of the AGPL. Your documents are unaffected: they stay yours and never
leave your computer.

---

<div align="center">
<sub>Made with 🐍 Python + <a href="https://flet.dev">Flet</a> · Powered by <a href="https://juanmaav92.github.io">@juanmaav92</a></sub>
</div>
