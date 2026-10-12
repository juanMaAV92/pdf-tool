# AGENTS.md

Guía para agentes de código (Claude Code, etc.) que trabajen en **pdf-tool**.

## Qué es

App de escritorio (Flet) **modular** para gestionar PDFs, pensada para usuarios **no técnicos**, multiplataforma (macOS + Windows), instalable y actualizable. Cada funcionalidad es una "herramienta" autocontenida que el host descubre y muestra. Actualmente incluye Comprimir, Imágenes a PDF, Unir, Proteger, Dividir y Marca de agua.

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
│   ├── jobs.py             # run_job(...) con JobHandle, cancelación y generaciones
│   ├── atomic.py           # publicación atómica de PDFs y copias
│   ├── batch.py            # run_batch(): bucle común de lotes (errores por archivo)
│   ├── config.py           # Settings en el dir de datos del usuario
│   ├── errors.py           # UserError y user_message(): mensajes para el usuario
│   ├── logger.py           # log rotativo con rutas y nombres redactados
│   ├── naming.py           # destinos y colisiones de nombres
│   ├── thumbnails.py       # render puro de miniaturas
│   └── updater.py          # is_newer(), check_for_update() vía GitHub Releases (nunca lanza)
├── ui/
│   ├── app.py              # host: NavigationRail + contenido + menú + banner update
│   ├── panel_base.py       # BaseToolPanel / SingleFileToolPanel: plantilla de panel
│   ├── file_list.py        # MultiFileToolPanel: lista de lote, resultados, miniaturas
│   ├── output_dir.py       # campo «Guardar en» (persistido en Settings)
│   ├── errors.py           # humanize_error() para la UI (delega en core/errors)
│   ├── accessibility.py    # NamedIconButton, HelpButton
│   ├── thumbnails.py       # carga asíncrona y caché de miniaturas
│   ├── logs.py             # «Descargar log»
│   ├── platform.py         # abrir archivo / carpeta en el SO
│   └── theme.py            # build_theme(), resolve_mode(), next_mode()
└── tools/
    ├── compress/
    ├── images2pdf/
    ├── merge/
    ├── protect/
    ├── split/
    └── watermark/          # cada carpeta contiene params.py, logic.py, panel.py e __init__.py
```

**Regla de oro:** `core/` no importa Flet. La lógica de cada herramienta (`logic.py`) es **pura** (sin Flet) y se testea sola; el `panel.py` solo arma la UI y delega en la lógica.

## Cómo agregar una herramienta nueva

No se toca el host. Crea `pdftool/tools/<id>/` con:

1. `params.py` — hereda de `BaseParams` (`pdftool/core/plugin.py`), no de
   `BaseModel` a secas: `BaseParams` aporta `output_dir`, y una herramienta que
   no lo herede ignorará en silencio la carpeta de salida que elija el usuario.
2. `logic.py` — función pura con la firma uniforme:
   ```python
   def run(inputs: list[Path], params: <Params>, progress: Progress = _noop) -> ToolResult: ...
   ```
   `inputs` es **siempre** `list[Path]` (1→1, N→1, 1→N). La ruta de salida **no
   se compone a mano**: se pide a `pdftool/core/naming.py`, que resuelve destino
   y colisiones en un solo sitio.
   ```python
   # nombre automático «<stem>_<sufijo>.pdf»
   out = output_path(input_path, "marca", out_dir=params.output_dir)
   # nombre libre (Unir, Imágenes a PDF)
   out = unique_path((params.output_dir or input_path.parent) / f"{base}.pdf")
   ```
   Con `output_dir=None` la salida va junto al original, que es el default.
   Ninguna herramienta debe sobrescribir un archivo existente: `unique_path`
   añade « (1)», « (2)»… y es la única fuente de esa regla.

   **Lotes (N→N):** no escribas el bucle a mano; usa
   `run_batch(inputs, process_one, progress, all_failed=...)` de
   `pdftool/core/batch.py`. Aísla el fallo de cada archivo en su `FileResult`,
   escala el progreso (`[i/N] nombre: …`) y deja pasar la cancelación.

   **Errores para el usuario:** lanza `UserError("mensaje en español")`
   (`pdftool/core/errors.py`) cuando el mensaje deba verse tal cual. Cualquier
   otra excepción se muestra como un mensaje genérico con el detalle plegado.
3. `panel.py` — clase decorada con `@register` que hereda la plantilla de la
   UI: `MultiFileToolPanel` (`pdftool/ui/file_list.py`) para lotes o
   `SingleFileToolPanel` (`pdftool/ui/panel_base.py`) para un archivo. Define
   `meta: ToolMeta` (con `order` para su posición en la navegación),
   `run_label`/`run_icon`/`pick_label` e implementa los hooks
   `extra_controls()`, `make_params()` y `run_logic(inputs, params, progress)`.
   `make_params()` lanza `InvalidParams("mensaje", field=campo)` para marcar el
   error también en el campo. En lotes, `reorderable = True` solo si el orden
   cambia el resultado (como en Unir).

   La base construye el panel **una vez por página** y lo reutiliza al volver
   a la herramienta: la lista, los campos, el resultado y el trabajo en curso
   se conservan. También ejecuta la lógica en segundo plano con `ctx.run_job`
   (con botón Cancelar); no lo llames tú salvo para lecturas propias del panel
   (p. ej. Dividir lee el número de páginas así, nunca en el hilo de la UI).
4. `__init__.py` — `from pdftool.tools.<id>.panel import <Tool>  # noqa: F401` para disparar el registro.

`discover()` la encuentra automáticamente y aparece en la barra lateral. Si una
herramienta falla al importarse, se registra en el log y el resto de la app
sigue funcionando; dos herramientas con el mismo `meta.id` son un error.

## Convenciones

- **TDD:** primero el test que falla (sobre la lógica pura), luego la implementación. Los paneles tienen tests de estado; la validación visual completa sigue siendo manual.
- **Tests de lógica pura** viven en `tests/` espejando la estructura. Fixtures de PDFs en `tests/conftest.py`.
- **Flet 0.28.x:** iconos y colores son enums **con mayúscula** (`ft.Icons.*`, `ft.Colors.*`). Tamaño de ventana: `page.window.width/height`. Abrir banner: `page.open(banner)`.
- Operaciones pesadas **siempre** en segundo plano vía `run_job` para no congelar la UI.

## Commits

- **NO** añadir trailers de co-autoría ni atribución de IA: nada de `Co-Authored-By: Claude`, ni `Generated with Claude Code`, ni similares. Mensajes planos.
- Estilo Conventional Commits: `feat(...)`, `fix(...)`, `chore(...)`, `docs(...)`.
- No commitear durante la implementación sin revisión salvo que se pida; el flujo del repo usa PRs contra `main`.

## Empaquetado y distribución

- macOS: `poetry run flet build macos` → `.app` → envolver en `.dmg`.
- Windows: `poetry run flet build windows` → compilar `installer/windows.iss` con Inno Setup → `pdf-tool-setup.exe` (actualiza en sitio, mismo `AppId`).
- Distribución por **GitHub Releases** con tag `vX.Y.Z`. El workflow de release toma la versión del tag; el repo del chequeo de actualizaciones está en `GITHUB_REPO` (`ui/app.py`).
- Los ajustes del usuario viven fuera del binario (`platformdirs`), así que sobreviven a las actualizaciones.

## Notas

- El proyecto usa **Flet 0.28.x**. CI fija **Flutter 3.29.3** (compatible con flet 0.28 y con VS 2022) y **Python 3.12** para `flet build`. flet 0.24.1 quedó obsoleto: no compilaba para Windows en los runners actuales.
- Las decisiones vigentes se documentan en `docs/roadmap.md` y `docs/deuda-tecnica.md`. Los specs y planes temporales no forman parte del repositorio y no se conservan cuando la funcionalidad ya está implementada.
