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

## Empaquetado

### macOS

```bash
poetry run flet build macos
# Resultado en build/macos -> crear .dmg arrastrando la .app
```

El usuario arrastra `pdf-tool.app` a Aplicaciones; al actualizar, Finder reemplaza la versión previa.

### Windows

```bash
poetry run flet build windows
# Luego compilar installer/windows.iss con Inno Setup -> pdf-tool-setup.exe
```

El instalador actualiza en sitio (mismo AppId).

## Distribución y actualizaciones

Publicar `pdf-tool.dmg` (Mac) y `pdf-tool-setup.exe` (Windows) en **GitHub Releases** con tag `vX.Y.Z`. La app consulta el último release al abrir y muestra un banner si hay versión nueva. Los ajustes del usuario viven fuera del binario (`platformdirs`), así que no se pierden al actualizar.

## Notas

- Ajusta `GITHUB_REPO` en `pdftool/ui/app.py` y `AppVersion` en `installer/windows.iss` al repo/versión reales antes del primer release.
- La firma/notarización (Gatekeeper en Mac, firma de código en Windows) queda fuera de v1.
