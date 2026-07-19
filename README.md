<div align="center">

# 📄 PDF Tool

**Una app de escritorio sencilla para trabajar con tus PDFs — sin subir nada a internet.**

<img width="980" height="680" alt="Screenshot 2026-06-15 at 6 54 49 PM" src="https://github.com/user-attachments/assets/adf416d8-bb05-478d-8a6d-31a35410af28" />

Comprime, une, divide, protege y marca tus documentos —y conviértelos desde imágenes—
desde tu propio ordenador. Gratis, de código abierto y sin anuncios.

[![Descargar](https://img.shields.io/badge/⬇️_Descargar-última_versión-2ea44f?style=for-the-badge)](https://github.com/juanMaAV92/pdf-tool/releases/latest)

[![CI](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/juanMaAV92/pdf-tool/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/juanMaAV92/pdf-tool?label=versión)](https://github.com/juanMaAV92/pdf-tool/releases/latest)
[![License: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/macOS_·_Windows-lightgrey)

</div>

<!-- 📸 Añade aquí un screenshot o GIF de la app:
     ![PDF Tool](docs/screenshot.png)
     Es lo que más convence a quien entra al repo. -->

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

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Puedes abrir un *issue* con ideas o errores,
o mandar un *pull request*. La arquitectura es modular: añadir una herramienta nueva
es crear una carpeta y la app la descubre sola. En el [roadmap](docs/roadmap.md)
está lo que viene (y lo que se descartó, con sus porqués).

<details>
<summary><b>🛠️ Para desarrolladores (montar el proyecto en local)</b></summary>

### Requisitos
- Python 3.11+ y [Poetry](https://python-poetry.org/)

### Arrancar
```bash
poetry install
poetry run pdftool        # abre la app
poetry run pytest         # corre los tests
```

### Añadir una herramienta nueva
1. Crea `pdftool/tools/<id>/` con `params.py`, `logic.py` (función pura + tests) y `panel.py`.
2. En `panel.py`, decora la clase con `@register` y define su `meta` (`ToolMeta`).
3. En `pdftool/tools/<id>/__init__.py` importa la clase para disparar el registro.
4. La app la descubre y la muestra automáticamente en la barra lateral.

La **lógica** (`logic.py`) no importa Flet y se prueba sin UI; la **UI** (`panel.py`)
solo arma controles. Esa separación mantiene los tests rápidos y la app desacoplada.

### Publicar una versión (automatizado con GitHub Actions)
```bash
git tag v0.2.0
git push origin v0.2.0
```
Eso dispara `release.yml`, que corre los tests, construye macOS (`.dmg`) y Windows
(instalador Inno Setup) en paralelo, hornea la versión del tag en el build y crea
un **GitHub Release en borrador** con ambos instaladores. Revísalo y pulsa
**Publish release** para que las apps instaladas detecten la actualización.

El número de versión es **el tag** — única fuente de verdad.

### Build local (para depurar el empaquetado)
```bash
poetry run flet build macos      # -> build/macos/pdf-tool.app
poetry run flet build windows    # -> build/windows/
```

</details>

---

<div align="center">
<sub>Hecho con 🐍 Python + <a href="https://flet.dev">Flet</a> · Licencia <a href="LICENSE">MIT</a></sub>
</div>
