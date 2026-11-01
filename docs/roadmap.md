# Roadmap

## Objetivo

Dar a conocer pdf-tool llevándolo a donde ya trabaja la gente: además de la app
de escritorio, una **CLI para agentes** (Claude Code, Cursor, Copilot…) publicada
en PyPI y una **skill** que les enseña a usarla. Gratis y de código abierto; la
difusión importa más que monetizar.

**Un solo repo, un solo proyecto.** Cada herramienta se define una vez (params +
lógica) y aparece a la vez en la app y en la CLI. Ninguna herramienta nueva
puede existir solo en una de las dos.

## Estado

Fases 1–4 hechas: la CLI está en PyPI (`pdf-tool-cli`, desde la v1.1.0) y el
plugin de Claude Code se instala desde este repo. Queda la Fase 5.

## Fase 1 — Núcleo de herramientas sin Flet ✅

Hoy el registro vive en `panel.py`, que importa Flet, y `ToolMeta.icon` usa
`ft.Icons`. Ningún consumidor sin UI puede descubrir las herramientas.

- Añadir `spec.py` por herramienta (sin Flet): id, nombre, descripción,
  categoría, orden, clase de params y función `run`. El registro se hace aquí.
- El icono y todo lo visual pasan a la UI; el panel se asocia a su spec.
- El contrato para agregar una herramienta queda: `params.py` + `logic.py` +
  `spec.py` + `panel.py`.

**Hecho cuando:** `import pdftool.core` y el descubrimiento de herramientas
funcionan sin Flet instalado, la app se comporta igual y la suite sigue verde.

## Fase 2 — CLI v1 ✅

- `pdf-tool list` y `pdf-tool <herramienta> --help`, generados desde el registro
  y los modelos Pydantic (flags, ayuda y validación salen de `params.py`).
- `--json`: resultado estructurado por archivo (`ToolResult` / `FileResult`,
  avisos y métricas) para que un agente lo interprete sin parsear texto.
- Códigos de salida claros (ok, fallo parcial del lote, error de uso).
- Secretos fuera de argv: la contraseña de Proteger por `--password-stdin` o
  variable de entorno.
- Mismas garantías que la app: nunca pisar originales (`core/naming.py`),
  publicación atómica, errores por archivo.

## Fase 3 — Publicación en PyPI ✅

- Nombre del paquete: `pdf-tool-cli` (PyPI rechaza `pdf-tool` por parecerse a `pdftool`); el comando sigue siendo `pdf-tool`.
- `pip install pdf-tool-cli` instala solo la CLI; Flet pasa a un extra `[gui]`.
- Riesgo principal: comprobar que `flet build` sigue empaquetando la app con
  Flet como dependencia opcional.
- Publicación automática desde el workflow de release (mismo tag `vX.Y.Z`).

**Hecho cuando:** `pipx install pdf-tool-cli` en una máquina limpia funciona y la
release sigue generando DMG e instalador.

## Fase 4 — Skill para agentes ✅

- `skills/pdf-tool/SKILL.md` en el repo: cuándo usar la CLI, cómo descubrir
  herramientas y cómo leer el `--json`.
- Instalable como plugin de Claude Code directamente desde GitHub.

## Fase 5 — Difusión (pendiente)

- README con la vía para agentes y una demo (un agente comprimiendo/uniendo).
- Listado gratuito en directorios de skills (p. ej. Agensi) tras revisar sus
  términos.

## Ideas futuras

Solo entran cumpliendo la regla de app y CLI a la par:

- Organizador de páginas: reordenar, rotar, eliminar y extraer.
- Inspeccionar y limpiar antes de compartir: metadatos, adjuntos, JavaScript
  (no es redacción).
- Recortar márgenes y ajustar tamaño de página.

## Fuera de foco

- Cobrar por la CLI o la skill.
- OCR, edición de contenido y AI/chat con documentos.
- Cambiar la experiencia de la app para sus usuarios no técnicos.
