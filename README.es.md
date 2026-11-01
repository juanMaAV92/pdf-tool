<div align="center">

# 📄 pdf-tool

**Herramientas de PDF locales para la línea de comandos, agentes de IA y el
escritorio. Nada sale de tu equipo.**

[English](https://github.com/juanMaAV92/pdf-tool/blob/main/README.md) · **Español**

[![PyPI](https://img.shields.io/pypi/v/pdf-tool-cli?label=PyPI)](https://pypi.org/project/pdf-tool-cli/)
[![CI](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/juanMaAV92/pdf-tool?label=versión)](https://github.com/juanMaAV92/pdf-tool/releases/latest)
[![Licencia](https://img.shields.io/badge/licencia-MIT_·_builds_AGPL-blue.svg)](#-licencia)
![Plataforma](https://img.shields.io/badge/macOS_·_Windows_·_Linux_(CLI)-lightgrey)

</div>

Une, divide, comprime, protege y marca PDFs, o convierte imágenes en PDF, con
una CLI pensada para scripts y agentes de IA, una skill para agentes y una app de
escritorio para todos los demás. Gratis, de código abierto, sin anuncios y
**100% sin conexión**: tus archivos nunca se suben a ningún sitio.

```bash
pipx install pdf-tool-cli
pdf-tool compress informe.pdf --target-mb 2
```

---

## 🧰 Herramientas

| Comando | Qué hace |
|---|---|
| `pdf-tool compress` | Reduce uno o varios PDFs a un tamaño objetivo en MB. |
| `pdf-tool merge` | Combina varios PDFs en uno, en el orden que indiques. |
| `pdf-tool split` | Divide un PDF por rangos de páginas, una página por archivo o cada N páginas. |
| `pdf-tool images2pdf` | Convierte cada imagen JPG/PNG en su propio PDF. |
| `pdf-tool protect` | Añade o quita la contraseña de uno o varios PDFs. |
| `pdf-tool watermark` | Repite un texto en diagonal sobre todas las páginas. |

Nunca sobrescribe tus archivos: la salida va junto al original (o a
`--output-dir`) con un nombre nuevo.

---

## ⌨️ Línea de comandos

```bash
pipx install pdf-tool-cli                          # o: uv tool install pdf-tool-cli
pdf-tool list --json                               # herramientas, entradas y parámetros
pdf-tool compress grande.pdf --target-mb 2 --json  # resultado en JSON
pdf-tool compress grande.pdf --target-mb 2 --mode preserve   # conserva texto y enlaces
pdf-tool merge a.pdf b.pdf c.pdf --output-name informe
pdf-tool split doc.pdf --ranges "1-3, 5, 8-"
printf '%s' "$CLAVE" | pdf-tool protect doc.pdf --password-stdin
```

- **Ayuda:** `pdf-tool <herramienta> --help` lista todas las opciones.
- **JSON para agentes:** `--json` imprime una estructura estable (`ok`,
  `summary`, `outputs`, `items` por archivo, `warnings`, `metrics` como el tamaño
  antes y después de comprimir).
- **Códigos de salida:** `0` ok · `1` error al procesar · `2` uso inválido ·
  `3` el lote terminó pero algún archivo falló.
- **Contraseñas:** se leen de stdin (`--password-stdin`) o de la variable
  `PDFTOOL_PASSWORD`, nunca de los argumentos.
- **Idioma:** los mensajes y los nombres de los archivos siguen el idioma del
  sistema; `--lang en` o `--lang es` lo cambian (o la variable `PDFTOOL_LANG`).
- **Modos de compresión:** `max` (por defecto) primero reduce las imágenes y solo
  convierte páginas en imagen si es la única forma de llegar al objetivo (lo
  avisa). `preserve` nunca lo hace, así que conserva texto, enlaces y
  anotaciones.

Requiere Python 3.11+. `pipx install 'pdf-tool-cli[gui]'` instala además la app
de escritorio (comando `pdftool`).

---

## 🤖 Úsala con agentes de IA

Una [skill](https://github.com/juanMaAV92/pdf-tool/blob/main/skills/pdf-tool/SKILL.md)
le enseña a tu agente a usar `pdf-tool` en lugar de escribir scripts
improvisados: pide permiso antes de instalar la CLI, ejecuta las herramientas con
`--json` y te explica el resultado en tu idioma. Sigue el formato abierto
[Agent Skills](https://agentskills.io), así que sirve para Claude Code, Codex,
Cursor, Gemini CLI, GitHub Copilot y otros.

<img width="760" alt="Claude Code usando la skill de pdf-tool para comprimir un PDF a 2 MB" src="https://raw.githubusercontent.com/juanMaAV92/pdf-tool/main/docs/agent-es.gif" />

Elige **una** vía:

**1. Claude Code (plugin, recomendado):** se actualiza solo desde `main`.

```text
/plugin marketplace add juanMaAV92/pdf-tool
/plugin install pdf-tool@pdf-tool
```

**2. Cualquier agente, con [`skills`](https://github.com/vercel-labs/skills)**
(requiere Node.js): detecta tus agentes y copia la skill a la carpeta de cada
uno. Añade `-g` para tenerla en todos tus proyectos; para actualizarla,
`npx skills update`.

```bash
npx skills add juanMaAV92/pdf-tool
```

**3. A mano:** copia la carpeta
[`skills/pdf-tool`](https://github.com/juanMaAV92/pdf-tool/tree/main/skills/pdf-tool)
en la carpeta de skills de tu agente
([rutas por agente](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)).
Para actualizarla, vuelve a copiarla.

En las tres vías la CLI se instala aparte (`pipx install pdf-tool-cli`); si
falta, la skill pide permiso para instalarla.

---

## 🖥️ App de escritorio

<img width="980" alt="App de escritorio de pdf-tool: pantalla de inicio con las seis herramientas" src="https://raw.githubusercontent.com/juanMaAV92/pdf-tool/main/docs/screenshot-es.png" />

Las mismas seis herramientas con una interfaz sencilla, en español o inglés, para
macOS y Windows. No necesita Python.

[![Descargar](https://img.shields.io/badge/⬇️_Descargar-última_versión-2ea44f?style=for-the-badge)](https://github.com/juanMaAV92/pdf-tool/releases/latest)

- **macOS:** abre el `.dmg` y arrastra **pdf-tool** a *Aplicaciones*. La app no
  está firmada, así que la primera vez ve a **Ajustes del Sistema → Privacidad y
  Seguridad** y pulsa **Abrir igualmente**.
- **Windows:** ejecuta el instalador. Si aparece SmartScreen: **Más
  información → Ejecutar de todas formas**.

Guía paso a paso, capturas y preguntas frecuentes:
**[juanmaav92.github.io/pdf-tool](https://juanmaav92.github.io/pdf-tool)**.
Cada versión publica `SHA256SUMS.txt` para que compruebes la descarga.

---

## 🤝 Contribuir

Los *issues* y *pull requests* son bienvenidos. Añadir una herramienta es crear
una carpeta: la app y la CLI la descubren solas. Las traducciones también son
bienvenidas: copia `pdftool/i18n/locales/en.json` como `<código>.json` y
tradúcelo. En el
[roadmap](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/roadmap.md) está
lo que viene.

<details>
<summary><b>🛠️ Para desarrolladores (montar el proyecto en local)</b></summary>

### Requisitos
- Python 3.11+ y [Poetry](https://python-poetry.org/)

### Arrancar
```bash
poetry install --all-extras   # incluye Flet (extra [gui]) para la app
poetry run pdftool            # abre la app
poetry run pdf-tool --help    # la CLI
poetry run pytest             # tests
```

### Añadir una herramienta
1. Crea `pdftool/tools/<id>/` con `params.py`, `logic.py` (función pura + tests),
   `spec.py` (registra la herramienta, sin Flet), `panel.py` y un `__init__.py`
   vacío.
2. Añade sus textos en `pdftool/i18n/locales/en.json` y `es.json`, y un ejemplo
   en la skill.
3. La app la muestra en la barra lateral y la CLI la ofrece como
   `pdf-tool <id>`, las dos automáticamente.

Detalles en [AGENTS.md](https://github.com/juanMaAV92/pdf-tool/blob/main/AGENTS.md) (en inglés).

### Publicar una versión (automatizado con GitHub Actions)
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
`release.yml` corre los tests, construye macOS (`.dmg`) y Windows (instalador
Inno Setup) en paralelo, hornea la versión del tag en el build y crea un
**GitHub Release en borrador** con ambos instaladores. Revísalo y pulsa
**Publish release** para que las apps instaladas detecten la actualización.
También publica el paquete en **PyPI** (`pdf-tool-cli`, por Trusted
Publishing); ese paso espera tu aprobación en Actions (entorno `pypi`), porque
una versión en PyPI no se puede reemplazar. El tag es la única fuente del número
de versión.

Los PRs que cambian la app, el empaquetado o sus dependencias ejecutan además
**Package smoke**, que construye el DMG de macOS e instala en silencio el
instalador de Windows. Antes de una release importante, sigue la
[checklist manual](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/release-smoke.md).

### Build local (para depurar el empaquetado)
```bash
poetry run flet build macos --project pdf-tool --product pdf-tool     # -> build/macos/pdf-tool.app
poetry run flet build windows --project pdf-tool --product pdf-tool   # -> build/windows/
```
`--project pdf-tool` es obligatorio: sin él, `flet build` toma el nombre del
paquete (`pdf-tool-cli`) y la app cambia de identidad.

</details>

---

## 📄 Licencia

El código de pdf-tool es [MIT](https://github.com/juanMaAV92/pdf-tool/blob/main/LICENSE).
Usa [PyMuPDF](https://pymupdf.readthedocs.io), con licencia AGPL, así que los
instaladores y el paquete de PyPI, que la incluyen, se distribuyen bajo los
términos de la AGPL. Para tus documentos no cambia nada: siguen siendo tuyos y no
salen de tu equipo.

---

<div align="center">
<sub>Hecho con 🐍 Python + <a href="https://flet.dev">Flet</a> · Powered by <a href="https://juanmaav92.github.io">@juanmaav92</a></sub>
</div>
