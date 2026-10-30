# AGENTS.md

Guía para agentes de código (Claude Code, etc.) que trabajen en **pdf-tool**.

## Qué es

App de escritorio (Flet) **modular** para gestionar PDFs, pensada para usuarios **no técnicos**, con una CLI (`pdf-tool`) para agentes generada de las mismas herramientas, multiplataforma (macOS + Windows), instalable y actualizable. Cada funcionalidad es una "herramienta" autocontenida que el host descubre y muestra. Actualmente incluye Comprimir, Imágenes a PDF, Unir, Proteger, Dividir y Marca de agua.

## Comandos

```bash
poetry install          # instalar dependencias
poetry run pdftool      # abrir la app de escritorio
poetry run pdf-tool list            # CLI: herramientas disponibles (--json para agentes)
poetry run pdf-tool compress a.pdf --json   # CLI: ejecutar una herramienta
poetry run pytest       # correr la suite de tests
poetry run pytest -v    # tests con detalle
poetry run ruff format pdftool tests && poetry run ruff check pdftool tests && poetry run mypy
                        # lo mismo que exige CI (mypy revisa todo el paquete)
pipx install pre-commit && pre-commit install   # opcional: lo anterior en cada commit
```

> **No actives venvs a mano** (`source .../activate`). Usa siempre `poetry run`; el entorno del proyecto lo gestiona Poetry. Activar otro venv provoca el error `[Errno 2] ... 'python'` al lanzar Flet.

## Arquitectura

```
pdftool/
├── main.py                 # entrypoint -> ft.app(target=build_app)
├── cli/                    # `pdf-tool`, SIN Flet: subcomandos desde el registro de specs
│   ├── __init__.py         # main(): list, <herramienta>, --json, códigos de salida 0/1/2/3
│   ├── args.py             # params Pydantic -> flags argparse (secretos por stdin/env)
│   └── report.py           # ToolResult -> texto o JSON
├── core/                   # SIN dependencia de Flet (testeable en aislamiento)
│   ├── plugin.py           # contrato: ToolMeta, ToolSpec, ToolResult, ToolContext, Progress, PdfTool
│   ├── registry.py         # specs sin Flet: register(), get_specs(), discover() (app y CLI)
│   ├── jobs.py             # run_job(...) con JobHandle, cancelación y generaciones
│   ├── atomic.py           # publicación atómica de PDFs y copias
│   ├── batch.py            # run_batch(): bucle común de lotes (errores por archivo)
│   ├── config.py           # Settings versionados; settings.tool(id) para preferencias propias
│   ├── errors.py           # UserError y user_message(): mensajes para el usuario
│   ├── logger.py           # log rotativo con rutas y nombres redactados
│   ├── naming.py           # destinos y colisiones de nombres
│   ├── thumbnails.py       # render puro de miniaturas
│   └── updater.py          # GITHUB_REPO, check_for_update() vía GitHub Releases (nunca lanza)
├── ui/
│   ├── app.py              # host: NavigationRail + contenido + menú + banner update
│   ├── panel_base.py       # BaseToolPanel / SingleFileToolPanel: plantilla de panel
│   ├── registry.py         # paneles: @register, get_tools(), discover()
│   ├── file_list.py        # MultiFileToolPanel: lista de lote, resultados, miniaturas
│   ├── output_dir.py       # campo «Guardar en» (persistido en Settings)
│   ├── errors.py           # humanize_error() para la UI (delega en core/errors)
│   ├── accessibility.py    # NamedIconButton, HelpButton
│   ├── thumbnails.py       # carga paralela por (ruta, página), caché por mtime
│   ├── logs.py             # «Descargar log»
│   ├── platform.py         # abrir archivo / carpeta en el SO
│   └── theme.py            # build_theme(), resolve_mode(), next_mode()
└── tools/
    ├── compress/
    ├── images2pdf/
    ├── merge/
    ├── protect/
    ├── split/
    └── watermark/          # cada carpeta: params.py, logic.py, spec.py, panel.py e __init__.py vacío
```

**Regla de oro:** `core/` no importa Flet. La lógica de cada herramienta (`logic.py`) es **pura** (sin Flet) y se testea sola; su `spec.py` la publica sin Flet para la app y la futura CLI; el `panel.py` solo arma la UI y delega en la spec.

## Cómo agregar una herramienta nueva

No se toca el host. Crea `pdftool/tools/<id>/` con:

1. `params.py` — hereda de `BaseParams` (`pdftool/core/plugin.py`), no de
   `BaseModel` a secas: `BaseParams` aporta `output_dir`, y una herramienta que
   no lo herede ignorará en silencio la carpeta de salida que elija el usuario.
   Cada campo lleva `Field(description=...)`: es la ayuda de `pdf-tool <id>
   --help` (un test lo exige). Un secreto (contraseña) lleva
   `json_schema_extra={"secret": True}` y la CLI solo lo acepta por stdin o
   variable de entorno. La validación va en el modelo (`field_validator`), no
   en el panel, para que la app y la CLI la compartan.
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
   `process_one` puede devolver `(salida, mensaje)` o un `Outcome` con
   `warnings` y `metrics` cuando el usuario debe saber algo del resultado (p.
   ej. «se rasterizaron páginas»; tamaños y % ahorrado). La UI muestra los
   avisos bajo el resumen y en la fila del archivo, sin diálogos.

   **Errores para el usuario:** lanza `UserError("mensaje en español")`
   (`pdftool/core/errors.py`) cuando el mensaje deba verse tal cual. Cualquier
   otra excepción se muestra como un mensaje genérico con el detalle plegado.
3. `spec.py` — **sin Flet**. Declara y registra la herramienta para la app y
   la CLI:
   ```python
   SPEC = register(ToolSpec(meta=ToolMeta(id=..., name=..., description=...,
                                          category=..., order=...),
                            params=<Params>, run=<función de logic.py>,
                            min_inputs=1, max_inputs=None, extensions=("pdf",)))
   ```
   (`register` de `pdftool/core/registry.py`; `order` fija su posición en la
   navegación). Las reglas de entrada valen para la app (el panel las hereda)
   y para la CLI. La CLI no se toca: la herramienta aparece sola en
   `pdf-tool list`.
4. `panel.py` — clase decorada con `@register` (`pdftool/ui/registry.py`) que
   hereda la plantilla de la UI: `MultiFileToolPanel` (`pdftool/ui/file_list.py`)
   para lotes o `SingleFileToolPanel` (`pdftool/ui/panel_base.py`) para un
   archivo. Declara `spec = SPEC` (de ahí salen `meta` y la lógica),
   `icon = ft.Icons.*`, `run_label`/`run_icon`/`pick_label` e implementa los
   hooks `extra_controls()` y `make_params()`.
   `make_params()` lanza `InvalidParams("mensaje", field=campo)` para marcar el
   error también en el campo. En lotes, `reorderable = True` solo si el orden
   cambia el resultado (como en Unir).

   La base construye el panel **una vez por página** y lo reutiliza al volver
   a la herramienta: la lista, los campos, el resultado y el trabajo en curso
   se conservan. También ejecuta la lógica en segundo plano con `ctx.run_job`
   (con botón Cancelar); no lo llames tú salvo para lecturas propias del panel
   (p. ej. Dividir lee el número de páginas así, nunca en el hilo de la UI).
5. `__init__.py` — vacío. El descubrimiento importa `spec.py` (núcleo) y
   `panel.py` (UI) por su cuenta.

**App y CLI a la par:** toda spec necesita su panel y viceversa; lo exige
`tests/ui/test_registry.py::test_every_spec_has_a_panel_and_vice_versa`. Y
`tests/core/test_no_flet.py` comprueba que las specs se descubren sin Flet.

`discover()` la encuentra automáticamente y aparece en la barra lateral, en el
grupo de su `meta.category` (la barra tiene scroll, así que caben muchas). Si una
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
- Distribución por **GitHub Releases** con tag `vX.Y.Z`. El workflow de release toma la versión del tag; el repo del chequeo de actualizaciones está en `GITHUB_REPO` (`core/updater.py`).
- La release publica `SHA256SUMS.txt` y una attestation de procedencia (`gh attestation verify`). Las actions van fijadas por SHA (Dependabot las actualiza) y Poetry, el plugin de export e Inno Setup por versión.
- CI corre `pip-audit` sobre las dependencias de ejecución. Una vulnerabilidad sin arreglo compatible se ignora explícitamente en `ci.yml`, con el motivo.
- Los ajustes del usuario viven fuera del binario (`platformdirs`), así que sobreviven a las actualizaciones.

## Notas

- El proyecto usa **Flet 0.28.x**. CI fija **Flutter 3.29.3** (compatible con flet 0.28 y con VS 2022) y **Python 3.12** para `flet build`. flet 0.24.1 quedó obsoleto: no compilaba para Windows en los runners actuales.
- La dirección vigente está en `docs/roadmap.md` (CLI para agentes en PyPI, a la par con la app). El pin de Flet 0.28.2 se explica en `pyproject.toml`. Los specs y planes temporales no forman parte del repositorio y no se conservan cuando la funcionalidad ya está implementada.
