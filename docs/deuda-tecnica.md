# Deuda técnica

Deuda **registrada como decisión, no como accidente** (mismo espíritu que el
roadmap): cada ítem dice qué es, por qué se acepta hoy, y — lo importante — el
**disparador** concreto que obliga a pagarla. Si el disparador llega y la deuda
sigue aquí sin pagar, eso sí es un problema.

Origen: evaluación de arquitectura del 2026-07-18, tras los PRs #16-#23.

## Activa — con disparador

### 1. `panel_base.py` es el hotspot universal (~526 líneas)

- **Qué:** acumula manejo de errores, acciones del footer, sanitización de nombres,
  `SingleFileToolPanel`, `MultiFileToolPanel` y el wiring de miniaturas. Empezó el
  2026-07-18 en ~315 líneas; cada feature de UI pasa por él.
- **Por qué se acepta:** sigue siendo legible y cohesivo; partirlo hoy sería
  refactor especulativo. La carpeta de salida (2026-07-26) se contuvo a propósito:
  el selector nació en `ui/output_dir.py` y `panel_base` solo lo instancia,
  sincroniza e inyecta en `do_run` — 9 líneas en vez de un widget entero. **Quedan
  ~24 líneas de margen**, así que la siguiente feature de UI paga la deuda.
- **Disparador:** ANTES de construir la cuadrícula de páginas (rotar/extraer/
  Dividir visual, ítems 6-7 del roadmap), o si supera ~550 líneas — lo que ocurra
  primero. Pago: extraer `MultiFileToolPanel` (o los widgets de fila) a su propio
  módulo; la cuadrícula nace en archivo propio, nunca dentro de `panel_base`.

### 3. Concurrencia acotada y cancelación cooperativa — pagada

- **Qué había:** `page.update()` desde hilos daemon y tareas de miniaturas
  creadas una por refresco dejaban la seguridad a convenciones locales.
- **Qué hay ahora:** `JobHandle` invalida callbacks obsoletos mediante generación
  y solicita cancelación cooperativa en cada progreso. Las miniaturas usan un
  `ThreadPoolExecutor` compartido limitado a dos workers, cancelan tareas
  pendientes y conservan su token de generación. El executor se libera al cerrar
  o desconectar la app.
- **Límite conocido:** una operación PDF que esté dentro de una llamada pesada de
  PyMuPDF no puede interrumpirse hasta volver a reportar progreso; la cancelación
  no es forzada. Si una feature necesita granularidad más fina, debe reportar
  avance por página o archivo.

### 4. Tests de UI de estado, no de píxeles

- **Qué:** los tests de paneles ejercitan lógica con stubs y `_FakePage`; nadie
  renderiza Flet de verdad. Un upgrade de Flet podría romper lo visual con la
  suite en verde.
- **Mitigación vigente:** Flet pineado (0.28.x), un smoke test que construye el
  panel real de Unir, ejecuta `run_job` real y valida un PDF de salida real, más
  verificación manual por PR (checklist en cada plan). El smoke test no abre
  diálogos nativos ni renderiza una ventana Flet, por lo que no reemplaza una
  prueba visual multiplataforma.
- **Disparador:** el próximo upgrade de versión de Flet. Pago mínimo: un smoke
  test con renderer/diálogo nativo que arranque la app y recorra un flujo (unir
  2 PDFs) antes de aceptar el upgrade.

### 5. Pin de Flet en 0.28.2 mientras la serie actual va por 0.86.x

- **Qué:** Flet 1.0 (0.70 alpha → 0.80 beta → 0.86 hoy) es una reescritura del
  framework, no un upgrade: los propios docs dicen que no es drop-in y recomiendan
  pinear 0.28.3 a quien no migre. Coste estimado de migrar: ~2-4 sesiones sobre
  las ~1.200 líneas de `ui/` y `tools/*/panel.py`. **La lógica PDF no se toca** —
  `core/` no importa Flet y cada herramienta separa `logic.py` de `panel.py`, así
  que 132 de los 243 tests son inmunes.
- **Dónde duele:** `FilePicker` dejó de ser un control y pasó a ser un *servicio*
  registrado en `page.services`, con métodos async que devuelven el resultado
  directamente — **`on_result` desaparece**. Eso es el patrón central de
  `panel_base.py` (picker reutilizado en `page.overlay`), `logs.py` y `app.py`, y
  toca todos los paneles. El resto es mecánico: `ft.app` → `ft.run`, `ft.ImageFit`
  → `ft.BoxFit`, `ft.alignment.center` → `ft.Alignment.CENTER`, `text=` → `label=`
  en ~14 botones, y `ft.dropdown` en minúscula.
- **Por qué se acepta:** el pin existe por el bug de file picker en macOS
  ([#5334](https://github.com/flet-dev/flet/issues/5334)) y la app funciona. Lo
  único que la migración desbloquea hoy es el drag & drop desde el SO, el ítem de
  menor prioridad del roadmap. Además hay bugs de `FilePicker` como servicio
  reportados en 0.80/0.81 ([#6040](https://github.com/flet-dev/flet/issues/6040),
  [#6251](https://github.com/flet-dev/flet/issues/6251)): antes de comprometerse
  hay que verificar que 0.86 abre diálogos limpio en macOS y Windows.
- **Disparador:** que un feature del roadmap necesite algo que 0.28 no da, que
  aparezca un bug de Flet sin workaround, o que el pin cumpla dos años (julio
  2027) — lo que ocurra primero. **Pago mínimo previo:** el smoke test E2E de la
  deuda #4. Los 111 tests que tocan UI usan `_FakePage` y stubs, así que pasarían
  verdes con la app visualmente rota; durante la migración la suite no protege.

## Aceptada — sin acción prevista

Registrado para que nadie lo "redescubra" como bug:

- **N `page.update()` secuenciales al cargar miniaturas de lotes grandes** (uno
  por render). No bloquea la UI; optimizable a `box.update()` con guarda si algún
  día se nota con 100+ archivos. (Review final de #23.)
- **Render duplicado si dos `load_async` concurrentes se cruzan con el mismo
  path**: CPU desperdiciada, nunca corrupción (`_store` idempotente y con lock).
  Documentado en el docstring del loader.
- **Rama "página de tamaño cero" del motor de miniaturas sin test** (difícil de
  construir un PDF así; la rama existe por defensa).
- **`except Exception` amplio en `render_thumbnail`**: deliberado — el fallo de
  render es estado del dominio (→ icono genérico), no excepción. Documentado en
  el docstring.
- **Caché de miniaturas sin invalidación por mtime**: editar un archivo en disco
  con la app abierta no refresca su miniatura en esa sesión. (Spec de thumbnails,
  fuera de alcance.)
- **`get_cached` sin anotación de retorno** por el sentinel `MISSING`; el
  docstring hace el trabajo.

## Pagada recientemente

- **Resultados por archivo:** el mapeo fila→salida dependía de prefijos de texto
  y posición; el review final de #22 ya había encontrado ese fallo en Comprimir.
  Ahora `ToolResult.items` contiene `FileResult` con entrada, salida, estado y
  mensaje. Comprimir, Imágenes a PDF, Proteger y `MultiFileToolPanel` usan el
  contrato estructurado; los tests cubren éxitos y fallos parciales.
- **Persistencia de ajustes:** `load_settings` vuelve a valores por defecto si
  el JSON falta, está corrupto o contiene valores inválidos. `save_settings`
  publica el archivo mediante escritura atómica, evitando dejar un
  `settings.json` parcial tras un cierre inesperado.
- **Smoke de integración:** cubre el recorrido panel real → job real → operación
  PDF real sin depender de una ventana nativa; la cobertura visual/packaged
  sigue siendo deuda activa #4.
