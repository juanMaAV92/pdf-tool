# AGENTS.md

Guía para agentes de código (Claude Code, etc.) que trabajen en **pdf-tool**.

## Qué es

App de escritorio (Flet) **modular** para gestionar PDFs, pensada para usuarios **no técnicos**, multiplataforma (macOS + Windows), instalable y actualizable. Cada funcionalidad es una "herramienta" autocontenida que el host descubre y muestra. Primera herramienta: **Comprimir PDF**.

## Comandos

```bash
poetry install          # instalar dependencias
poetry run pdftool      # abrir la app de escritorio
poetry run pytest       # correr la suite de tests
poetry run pytest -v    # tests con detalle
```

> **No actives venvs a mano** (`source .../activate`). Usa siempre `poetry run`; el entorno del proyecto lo gestiona Poetry. Activar otro venv provoca el error `[Errno 2] ... 'python'` al lanzar Flet.

## Arquitectura

```
pdftool/
├── main.py                 # entrypoint -> ft.app(target=build_app)
├── core/                   # SIN dependencia de Flet (testeable en aislamiento)
│   ├── plugin.py           # contrato: ToolMeta, ToolResult, ToolContext, Progress, PdfTool
│   ├── registry.py         # @register, get_tools(), discover()
│   ├── jobs.py             # run_job(work, on_progress, on_done, on_error) en hilo daemon
│   ├── config.py           # Settings (pydantic) en el dir de datos del usuario (platformdirs)
│   └── updater.py          # is_newer(), check_for_update() vía GitHub Releases (nunca lanza)
├── ui/
│   ├── theme.py            # build_theme(), resolve_mode(), next_mode() (claro/oscuro/sistema)
│   └── app.py              # host: NavigationRail + contenido + toggle tema + banner update
└── tools/
    └── compress/
        ├── __init__.py     # importa el panel para disparar @register
        ├── params.py       # CompressParams (pydantic)
        ├── logic.py        # compress() PURO (sin Flet) + output_path_for()
        └── panel.py        # CompressTool(PdfTool): UI Flet
```

**Regla de oro:** `core/` no importa Flet. La lógica de cada herramienta (`logic.py`) es **pura** (sin Flet) y se testea sola; el `panel.py` solo arma la UI y delega en la lógica.

## Cómo agregar una herramienta nueva

No se toca el host. Crea `pdftool/tools/<id>/` con:

1. `params.py` — un `BaseModel` de pydantic con los parámetros.
2. `logic.py` — función pura con la firma uniforme:
   ```python
   def run(inputs: list[Path], params: <Params>, progress: Progress = _noop) -> ToolResult: ...
   ```
   `inputs` es **siempre** `list[Path]` (1→1, N→1, 1→N). La salida va **junto al archivo original**.
3. `panel.py` — clase que hereda `PdfTool`, decorada con `@register`, define `meta: ToolMeta` y `build_panel(ctx)`. Usa `ctx.run_job(...)` para correr la lógica en segundo plano.
4. `__init__.py` — `from pdftool.tools.<id>.panel import <Tool>  # noqa: F401` para disparar el registro.

`discover()` la encuentra automáticamente y aparece en la barra lateral.

## Convenciones

- **TDD:** primero el test que falla (sobre la lógica pura), luego la implementación. Los paneles Flet se verifican manualmente.
- **Tests de lógica pura** viven en `tests/` espejando la estructura. Fixtures de PDFs en `tests/conftest.py`.
- **Flet 0.24.1:** iconos y colores son **minúsculas** (`ft.icons.*`, `ft.colors.*`), NO `ft.Icons`/`ft.Colors`. Tamaño de ventana: `page.window.width/height`. Abrir banner: `page.open(banner)`.
- Operaciones pesadas **siempre** en segundo plano vía `run_job` para no congelar la UI.

## Commits

- **NO** añadir trailers de co-autoría ni atribución de IA: nada de `Co-Authored-By: Claude`, ni `Generated with Claude Code`, ni similares. Mensajes planos.
- Estilo Conventional Commits: `feat(...)`, `fix(...)`, `chore(...)`, `docs(...)`.
- No commitear durante la implementación sin revisión salvo que se pida; el flujo del repo usa PRs contra `main`.

## Empaquetado y distribución

- macOS: `poetry run flet build macos` → `.app` → envolver en `.dmg`.
- Windows: `poetry run flet build windows` → compilar `installer/windows.iss` con Inno Setup → `pdf-tool-setup.exe` (actualiza en sitio, mismo `AppId`).
- Distribución por **GitHub Releases** con tag `vX.Y.Z`. Ajustar `GITHUB_REPO` en `ui/app.py` y `AppVersion` en `installer/windows.iss` antes del primer release.
- Los ajustes del usuario viven fuera del binario (`platformdirs`), así que sobreviven a las actualizaciones.

## Notas

- El proyecto corre sobre **Python 3.14** con **Flet 0.24.1**. Si el empaquetado (`flet build`) da problemas, considerar fijar Python a 3.12 o subir Flet.
- `docs/superpowers/` (specs y planes de diseño) está en `.gitignore` — es referencia local, no va al repo.
