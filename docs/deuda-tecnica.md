# Deuda técnica

Deuda **registrada como decisión, no como accidente** (mismo espíritu que el
roadmap): cada ítem dice qué es, por qué se acepta hoy, y — lo importante — el
**disparador** concreto que obliga a pagarla. Si el disparador llega y la deuda
sigue aquí sin pagar, eso sí es un problema.

Origen: evaluación de arquitectura del 2026-07-18, tras los PRs #16-#23.

## Activa — con disparador

### 1. `panel_base.py` es el hotspot universal (~460 líneas)

- **Qué:** acumula manejo de errores, acciones del footer, sanitización de nombres,
  `SingleFileToolPanel`, `MultiFileToolPanel` y el wiring de miniaturas. Empezó el
  2026-07-18 en ~315 líneas; cada feature de UI pasa por él.
- **Por qué se acepta:** sigue siendo legible y cohesivo; partirlo hoy sería
  refactor especulativo.
- **Disparador:** ANTES de construir la cuadrícula de páginas (rotar/extraer/
  Dividir visual, ítems 6-7 del roadmap), o si supera ~550 líneas — lo que ocurra
  primero. Pago: extraer `MultiFileToolPanel` (o los widgets de fila) a su propio
  módulo; la cuadrícula nace en archivo propio, nunca dentro de `panel_base`.

### 2. `ToolResult` es "stringly-typed" para resultados por archivo

- **Qué:** el mapeo fila→salida en lotes depende de convenciones de texto: la
  etiqueta de éxito empieza por `"→ "` y la correspondencia con `outputs` es
  posicional. `MultiFileToolPanel.on_result` aplica una regla doble (posicional si
  no hubo fallos; prefijo si los hubo) con guarda anti-IndexError.
- **Evidencia de que muerde:** el review final de #22 encontró los iconos de fila
  silenciosamente rotos en Comprimir — sus etiquetas (`"1.23 MB → 0.45 MB"`)
  contienen "→" pero no empiezan por él. Se corrigió con la regla doble; la
  fragilidad de fondo quedó.
- **Por qué se acepta:** dos consumidores, contrato documentado en código y spec,
  test de regresión con etiquetas reales de Comprimir.
- **Disparador:** ANTES de las features de páginas (que multiplican los
  consumidores del contrato), o al tercer bug de mapeo. Pago: estructurar el
  contrato — `ToolResult.items: list[FileResult(path, label, ok)]` — y migrar los
  4 tools de lote y el panel en un solo PR.

### 3. Concurrencia por convención, no por diseño

- **Qué:** `page.update()` desde hilos daemon + tokens de generación funcionan
  (es la norma de Flet y el patrón de `run_job`), pero cada feature async
  re-deriva su seguridad a mano. Hoy hay dos: el job de herramienta y el loader
  de miniaturas; pueden solaparse (Flet serializa los envíos — riesgo bajo).
- **Disparador:** la TERCERA feature async (probable: render de la cuadrícula de
  páginas). Pago: helper común tipo "actualiza este control si la generación
  sigue vigente", usado por todos.

### 4. Tests de UI de estado, no de píxeles

- **Qué:** los tests de paneles ejercitan lógica con stubs y `_FakePage`; nadie
  renderiza Flet de verdad. Un upgrade de Flet podría romper lo visual con la
  suite en verde.
- **Mitigación vigente:** Flet pineado (0.28.x) + verificación manual por PR
  (checklist en cada plan).
- **Disparador:** el próximo upgrade de versión de Flet. Pago mínimo: un smoke
  test E2E que arranque la app y recorra un flujo (unir 2 PDFs) antes de aceptar
  el upgrade.

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
