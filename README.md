# pdf-tool

App de escritorio para gestionar PDFs (modular). Primera herramienta: **Comprimir PDF**.

## Desarrollo

```bash
poetry install
poetry run pdftool        # abre la app
poetry run pytest          # corre los tests
```

## Agregar una herramienta nueva

1. Crea `pdftool/tools/<id>/` con `params.py`, `logic.py` (función pura + tests) y `panel.py`.
2. En `panel.py`, decora la clase con `@register` y define su `meta` (`ToolMeta`).
3. En `pdftool/tools/<id>/__init__.py` importa la clase para disparar el registro.
4. La app la descubre y la muestra automáticamente en la barra lateral.

## Releases (automatizado con GitHub Actions)

No se empaqueta a mano. Para publicar una nueva versión:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Eso dispara `.github/workflows/release.yml`, que:

1. Corre los tests (si fallan, no construye nada).
2. Construye en paralelo macOS (`.dmg`) y Windows (instalador Inno Setup).
3. Hornea la versión del tag en el build (`pyproject`, `__version__`, `AppVersion`).
4. Crea un **GitHub Release en borrador** con ambos instaladores adjuntos.

Revisa el borrador y, cuando estés conforme, publícalo (botón **Publish release**
o `gh release edit v0.2.0 --draft=false`). Solo al publicarlo las apps instaladas
detectan la nueva versión y muestran el banner de actualización.

El número de versión es **el tag** — única fuente de verdad; no edites versiones a mano.

### Build local (para depurar el empaquetado)

```bash
poetry run flet build macos      # -> build/macos/pdf-tool.app
poetry run flet build windows    # -> build/windows/  (luego compilar installer/windows.iss)
```

### Cómo abrir la app sin firma

Los instaladores no están firmados (Gatekeeper / SmartScreen avisarán):

- **macOS:** clic derecho sobre la app → **Abrir** → **Abrir** (solo la 1ª vez).
  Si dice "dañada": `xattr -dr com.apple.quarantine /Applications/pdf-tool.app`.
- **Windows:** en SmartScreen → **Más información** → **Ejecutar de todas formas**.

Los ajustes del usuario viven fuera del binario (`platformdirs`), así que se conservan al actualizar.

## Notas

- Antes del primer release, ajusta `GITHUB_REPO` en `pdftool/ui/app.py` al repo real
  (`juanMaAV92/pdf-tool`) para que el chequeo de actualización apunte bien.
- CI usa Python 3.12 (más estable para `flet build` que 3.14). La firma/notarización queda fuera de v1.
