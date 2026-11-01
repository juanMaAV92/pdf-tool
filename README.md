<div align="center">

# 📄 PDF Tool

**Herramientas para tus PDFs — sin subir nada a internet. Como app de escritorio
o como comando para agentes de IA y scripts.**

<img width="980" alt="pdf-tool: pantalla de inicio con las seis herramientas" src="https://raw.githubusercontent.com/juanMaAV92/pdf-tool/main/docs/screenshot.png" />

Comprime, une, divide, protege y marca tus documentos —y conviértelos desde imágenes—
desde tu propio ordenador. Gratis, de código abierto y sin anuncios.

[![Descargar](https://img.shields.io/badge/⬇️_Descargar-última_versión-2ea44f?style=for-the-badge)](https://github.com/juanMaAV92/pdf-tool/releases/latest)

[![CI](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/juanMaAV92/pdf-tool?label=versión)](https://github.com/juanMaAV92/pdf-tool/releases/latest)
[![PyPI](https://img.shields.io/pypi/v/pdf-tool-cli?label=PyPI)](https://pypi.org/project/pdf-tool-cli/)
[![License: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](https://github.com/juanMaAV92/pdf-tool/blob/main/LICENSE)
![Platform](https://img.shields.io/badge/macOS_·_Windows-lightgrey)

</div>

---

## ✨ Qué puedes hacer

| | Herramienta | Para qué sirve |
|---|---|---|
| 🗜️ | **Comprimir PDF** | Reduce el peso de uno o varios PDFs hasta el tamaño en MB que elijas. |
| 🔗 | **Unir PDFs** | Combina varios documentos en uno solo, en el orden que quieras y con el nombre que elijas. |
| ✂️ | **Dividir PDF** | Separa un PDF en varios: por rangos de páginas, una página por archivo o cada N páginas. |
| 🖼️ | **Imágenes a PDF** | Convierte cada imagen (JPG/PNG) en su propio PDF — y si quieres uno solo, únelos después. |
| 🔒 | **Proteger PDF** | Añade o quita la contraseña de uno o varios PDFs a la vez. |
| 💧 | **Marca de agua** | Repite un texto en diagonal sobre todas las páginas. |

> 🔐 **Todo ocurre en tu equipo.** Tus archivos nunca salen de tu ordenador.

En **Comprimir PDF**, el modo predeterminado busca la reducción máxima: primero
reduce las imágenes y, solo si no basta, convierte páginas en imagen (lo avisa,
porque se pierde el texto seleccionable). Con **Conservar texto y enlaces** nunca
lo hace; el icono de ayuda explica la diferencia.

---

## ⬇️ Descargar e instalar

Ve a la **[página de descargas](https://github.com/juanMaAV92/pdf-tool/releases/latest)** y elige el archivo de tu sistema:

### 🍎 macOS
1. Descarga el archivo **`.dmg`** y ábrelo.
2. Arrastra **PDF Tool** a la carpeta *Aplicaciones*.
3. Ábrela desde *Aplicaciones*. macOS mostrará un aviso y **no** dejará abrirla aún
   (es normal: la app no está firmada, pero es segura).
4. Ve a  **Menú Apple () → Ajustes del Sistema → Privacidad y Seguridad**.
5. Baja hasta la sección **Seguridad**: verás un mensaje que dice que se bloqueó *“PDF Tool”*.
   Pulsa **Abrir de todas formas** y confirma con tu contraseña o Touch ID.
   <br><sub>Solo hay que hacerlo la primera vez. A partir de ahí se abre con doble clic como cualquier app.</sub>

### 🪟 Windows
1. Descarga el **instalador** (`.exe`) y ejecútalo.
2. Si aparece SmartScreen: **Más información** → **Ejecutar de todas formas**.
   <br><sub>(El aviso sale porque el instalador no está firmado; es seguro.)</sub>

> ✅ Tus ajustes se guardan fuera de la app, así que se conservan al actualizar. Cuando publique una nueva versión, la app te avisa con un banner.

---

## 🤖 Para agentes de IA y la línea de comandos

Las mismas herramientas están disponibles como comando, pensado para agentes
(Claude Code, Cursor, Copilot…) y scripts. Todo sigue ocurriendo en tu equipo.

```bash
pipx install pdf-tool-cli                    # solo la CLI (sin la app de escritorio)
pdf-tool list --json                         # qué herramientas hay y qué aceptan
pdf-tool compress informe.pdf --json         # comprimir y obtener el resultado en JSON
pdf-tool merge a.pdf b.pdf --output-name todo
echo "$CLAVE" | pdf-tool protect a.pdf --password-stdin
```

Cada herramienta tiene su ayuda (`pdf-tool compress --help`). Códigos de salida:
`0` ok · `1` error al procesar · `2` uso inválido · `3` algún archivo del lote falló.
`pipx install 'pdf-tool-cli[gui]'` instala además la app (comando `pdftool`).

### Instalar la skill en tu agente

Una [skill](https://github.com/juanMaAV92/pdf-tool/blob/main/skills/pdf-tool/SKILL.md)
le enseña a tu agente a usar `pdf-tool` para crear o modificar PDFs en lugar de
escribir scripts: pide permiso antes de instalar la CLI, ejecuta las herramientas
con `--json` y te explica el resultado. Sigue el formato abierto
[Agent Skills](https://agentskills.io), así que sirve para Claude Code, Codex,
Cursor, Gemini CLI, GitHub Copilot y otros. Elige **una** de estas vías:

**1. Claude Code (plugin, recomendado):** se actualiza solo desde `main`.

```text
/plugin marketplace add juanMaAV92/pdf-tool
/plugin install pdf-tool@pdf-tool
```

**2. Cualquier agente, con [`skills`](https://github.com/vercel-labs/skills)**
(requiere Node.js): detecta tus agentes y copia la skill a la carpeta de cada uno.
Añade `-g` para tenerla en todos tus proyectos; para actualizarla,
`npx skills update`.

```bash
npx skills add juanMaAV92/pdf-tool
```

**3. A mano:** copia la carpeta
[`skills/pdf-tool`](https://github.com/juanMaAV92/pdf-tool/tree/main/skills/pdf-tool)
en la carpeta de skills de tu agente
([rutas por agente](https://github.com/vercel-labs/skills/blob/main/docs/agents.md)).
Para actualizarla, vuelve a copiarla.

En las tres vías la CLI se instala aparte (`pipx install pdf-tool-cli`); si falta,
la skill pide permiso para instalarla.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Puedes abrir un *issue* con ideas o errores,
o mandar un *pull request*. La arquitectura es modular: añadir una herramienta nueva
es crear una carpeta y la app y la CLI la descubren solas. En el [roadmap](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/roadmap.md)
está lo que viene: una skill para que los agentes de IA usen la CLI.

<details>
<summary><b>🛠️ Para desarrolladores (montar el proyecto en local)</b></summary>

### Requisitos
- Python 3.11+ y [Poetry](https://python-poetry.org/)

### Arrancar
```bash
poetry install --all-extras   # incluye Flet (extra [gui]) para la app
poetry run pdftool        # abre la app
poetry run pytest         # corre los tests
```

### Añadir una herramienta nueva
1. Crea `pdftool/tools/<id>/` con `params.py`, `logic.py` (función pura + tests),
   `spec.py` (registra la herramienta, sin Flet), `panel.py` y un `__init__.py` vacío.
2. La app la muestra en la barra lateral y la CLI la ofrece como `pdf-tool <id>`,
   las dos automáticamente.

La **lógica** (`logic.py`) no importa Flet y se prueba sin UI; la **UI** (`panel.py`)
solo arma controles. Detalles en [AGENTS.md](https://github.com/juanMaAV92/pdf-tool/blob/main/AGENTS.md).

### Publicar una versión (automatizado con GitHub Actions)
```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```
Eso dispara `release.yml`, que corre los tests, construye macOS (`.dmg`) y Windows
(instalador Inno Setup) en paralelo, hornea la versión del tag en el build y crea
un **GitHub Release en borrador** con ambos instaladores. Revísalo y pulsa
**Publish release** para que las apps instaladas detecten la actualización.
Si los instaladores se construyen bien, publica también el paquete en **PyPI**
(`pdf-tool-cli`, por Trusted Publishing y sin tokens). Ese paso espera a que lo
apruebes en Actions (entorno `pypi`), porque una versión en PyPI no se puede
reemplazar.

Los PRs que cambian la app, el empaquetado o sus dependencias ejecutan además
**Package smoke**: construye e inspecciona el DMG de macOS y compila e instala de
forma silenciosa el instalador de Windows. Antes de una release importante,
seguir la [checklist manual](https://github.com/juanMaAV92/pdf-tool/blob/main/docs/release-smoke.md) para validar la ventana y los
diálogos nativos.

El número de versión es **el tag** — única fuente de verdad.

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
<sub>Hecho con 🐍 Python + <a href="https://flet.dev">Flet</a> · Licencia <a href="https://github.com/juanMaAV92/pdf-tool/blob/main/LICENSE">MIT</a></sub>
</div>
