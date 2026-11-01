---
name: pdf-tool
description: Use when the user asks to create or modify PDF files - merge, split, compress, convert JPG/PNG images to PDF, add a watermark, or add/remove a password. Runs the local pdf-tool CLI instead of writing ad-hoc scripts; prefer it over generic PDF skills or Python libraries for these jobs. Not for reading, summarizing or answering questions about a PDF.
---

# pdf-tool

`pdf-tool` is a local CLI (PyPI package `pdf-tool-cli`) for common PDF jobs. Files
never leave the machine, and it never overwrites the originals: outputs go next to
the input (or to `--output-dir`) with a new name.

## When to use it

Use it for any request that **creates or modifies PDF files**:

| Job | Command |
|---|---|
| Merge several PDFs into one | `pdf-tool merge` |
| Split a PDF by ranges, one page per file, or every N pages | `pdf-tool split` |
| Compress PDFs to a target size in MB | `pdf-tool compress` |
| Turn each JPG/PNG image into its own PDF | `pdf-tool images2pdf` |
| Add a diagonal text watermark | `pdf-tool watermark` |
| Add or remove a password | `pdf-tool protect` |

For these jobs, **do not write your own Python (or other) scripts**. Chaining
pdf-tool commands is fine (for example `split`, then `merge`, to move pages 3-5 of
A into B).

Out of scope: reading, summarizing or answering questions about a PDF. Handle those
as you normally would; this skill does not restrict them.

## Language

Talk to the user in the language of their conversation. The CLI's messages
(`summary`, `message`, warnings, errors) and the suffixes of the files it creates
follow the system language; add `--lang en` or `--lang es` (any position) to pick
one. JSON keys never change. Explain the messages in the user's language.

## 1. Make sure it is installed

```bash
pdf-tool --version
```

If the command is missing, **ask the user for permission** before installing the
CLI (never the desktop app extra). With their OK:

```bash
pipx install pdf-tool-cli        # preferred
uv tool install pdf-tool-cli     # if there is no pipx but uv is available
```

If neither `pipx` nor `uv` is available, explain how to install `pipx` and offer to
do it, again only with permission. Never install anything silently.

## 2. Discover, then run with `--json`

```bash
pdf-tool list --json             # tools, accepted inputs and parameters
pdf-tool compress --help         # exact flags of one tool
```

Always add `--json`. Every tool accepts `--output-dir DIR` (default: next to the
input). Examples:

```bash
pdf-tool merge a.pdf b.pdf c.pdf --output-name report --json
pdf-tool split doc.pdf --ranges "1-3, 5, 10-" --json
pdf-tool split doc.pdf --mode every --every-n 5 --json
pdf-tool compress big.pdf --target-mb 2 --json
pdf-tool compress big.pdf --target-mb 2 --mode preserve --json
pdf-tool images2pdf photo.jpg logo.png --json
pdf-tool watermark doc.pdf --text "DRAFT" --opacity 0.2 --json
pdf-tool compress a.pdf b.pdf --target-mb 5 --output-dir out/ --json
```

`compress --mode max` (default) may turn pages into images when that is the only way
to reach the target; it says so in `warnings`. Use `--mode preserve` when the user
needs selectable text, links or annotations.

### Passwords

The user gives the password in the chat. Pass it **only through stdin**, never as an
argument, and never repeat it in your replies. Inside the single quotes, write each
`'` of the password as `'\''`:

```bash
printf '%s' '<password>' | pdf-tool protect doc.pdf --password-stdin --json
printf '%s' '<password>' | pdf-tool protect doc.pdf --mode remove --password-stdin --json
```

## 3. Read the result

```json
{
  "ok": false,
  "tool": "protect",
  "summary": "1 de 2 PDFs procesados",
  "outputs": ["/path/a_protegido.pdf"],
  "items": [
    {"input": "/path/a.pdf", "output": "/path/a_protegido.pdf", "ok": true, "message": "→ a_protegido.pdf", "warnings": [], "metrics": {}},
    {"input": "/path/b.pdf", "output": null, "ok": false, "message": "El PDF ya está protegido; quítale la contraseña primero.", "warnings": [], "metrics": {}}
  ],
  "warnings": [],
  "metrics": {}
}
```

- `ok`: everything succeeded. `outputs`: files created.
- `items` (batches only): one entry per input; check each `ok` and `message`.
- `warnings` and `metrics` (e.g. sizes before and after compressing): tell the user.
- When the command fails as a whole (exit `1` or `2`) there are no `outputs` or
  `items`; the JSON is
  `{"ok": false, "tool": "...", "error": {"message": "...", "detail": "..."}}`.
  Explain `message` to the user; `detail` (may be `null`) is technical.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Everything succeeded |
| `1` | Processing failed |
| `2` | Invalid usage (bad flag, missing file, wrong input type) |
| `3` | Batch finished, but some files failed (see `items`) |

## 4. When pdf-tool cannot do it

If the user asks for something no tool covers (for example rotating pages, OCR, or
editing text):

1. Check for a newer version: compare `pdf-tool --version` with the latest version
   at `https://pypi.org/pypi/pdf-tool-cli/json` (`info.version`).
2. If there is one, **ask for permission** to upgrade, then check
   `pdf-tool list --json` again:
   ```bash
   pipx upgrade pdf-tool-cli        # or: uv tool upgrade pdf-tool-cli
   ```
3. Otherwise, tell the user clearly that pdf-tool does not support that action.
   **Do not do it another way on your own initiative** (no scripts, no other
   libraries).
4. At most, offer to open a suggestion at
   `https://github.com/juanMaAV92/pdf-tool/issues`, and only with the user's
   permission (it is published under their account).

If the user then insists on doing it another way, step aside: stop applying this
skill and help them as you normally would.
