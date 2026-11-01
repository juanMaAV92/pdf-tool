# Roadmap

## Objetivo

Ser la caja de herramientas de PDF **offline, gratuita y de código abierto** para
quien no quiere subir sus documentos a una web: la app de escritorio para usuarios
no técnicos y la CLI (con su skill) para desarrolladores y agentes de IA. La
difusión importa más que monetizar.

## Reglas que aplican a todo

- **App y CLI a la par.** Cada herramienta se define una vez (`params.py` +
  `logic.py` + `spec.py`) y aparece a la vez en la app y en la CLI, con su ejemplo
  en `skills/pdf-tool/SKILL.md`.
- **Presupuesto de peso.** Nada de OCR ni motores pesados. Toda dependencia nueva
  se justifica y pesa menos de ~10 MB; PyMuPDF (ya incluida) es la primera opción.
  Referencia en la v1.1.1: DMG 168 MB, instalador de Windows 91 MB.
- **Todo local.** Ninguna herramienta envía archivos ni datos fuera del equipo.
- **Multilenguaje desde la Fase 0.** Ningún texto visible se escribe en el código:
  todo sale de los diccionarios de traducción.

## Hecho

- **Fase 1:** núcleo de herramientas sin Flet (`spec.py`, registro sin UI).
- **Fase 2:** CLI v1 (`pdf-tool`, `--json`, códigos de salida, `--password-stdin`).
- **Fase 3:** publicación en PyPI como `pdf-tool-cli` (desde la v1.1.0), con Flet
  como extra `[gui]`.
- **Fase 4:** skill en formato abierto Agent Skills; plugin de Claude Code,
  `npx skills add` o copia manual.

## Fase 0 — Multilenguaje

**Objetivo:** app, CLI, README y página web en español e inglés, con un sistema en
el que **añadir un idioma sea añadir un diccionario**, sin tocar código.

### Diccionarios

- Un archivo por idioma en `pdftool/i18n/locales/<código>.json` (`es.json`,
  `en.json`; mañana `pt.json`). El módulo `pdftool/i18n/` no importa Flet: lo usan
  la app, la CLI y la lógica.
- Claves estables y por zonas, con datos variables como marcadores:
  ```json
  {
    "_meta": { "name": "English" },
    "compress.name": "Compress PDF",
    "compress.progress.page": "Compressing page {page} of {total}…",
    "batch.summary": { "one": "{count} PDF processed", "other": "{count} PDFs processed" }
  }
  ```
- `t("clave", **datos)` devuelve el texto en el idioma activo. Si una clave
  falta, usa el idioma base (**español**, el que se mantiene completo) y nunca
  rompe la app.
- Plurales: variantes `one` / `other` elegidas por `count`. Suficiente para
  español, inglés, portugués, francés…; los idiomas con más formas quedan para
  cuando alguien los pida.
- Los idiomas disponibles se descubren listando `locales/`: el selector de la app y
  `--lang` de la CLI los muestran solos, con el nombre de `_meta.name`.

### Idioma activo

- **App:** por defecto el del sistema; se puede cambiar en Ajustes (se guarda en
  `settings.json` como `language`: `"system"` o un código). Si el idioma del
  sistema no tiene diccionario, inglés.
- **CLI:** `--lang <código>`, o la variable `PDFTOOL_LANG`, o el idioma del sistema.
  El JSON no cambia: claves en inglés como hoy; solo se traducen los textos
  (`summary`, `message`, `warnings`, `error.message`). `error.detail` (técnico,
  p. ej. de PyMuPDF) queda tal cual.

### Qué se traduce

- Nombre, descripción y categoría de cada herramienta (`ToolMeta` guarda claves,
  no textos), la ayuda de cada parámetro (las `description` de `params.py`) y los
  textos de los paneles.
- Progreso, resúmenes, avisos y errores de la lógica y de `core/`.
- Los sufijos de los archivos de salida (`_comprimido` / `_compressed`). Hoy están
  mezclados (`_merged` en inglés, el resto en español); pasan a seguir el idioma.
- La skill deja de decir que los mensajes de la CLI salen en español.

### Garantías (tests)

- Cada diccionario tiene exactamente las claves del español y los mismos
  marcadores (`{page}`, `{total}`…) en cada texto.
- Ningún texto visible queda escrito en el código: un test recorre `pdftool/` y
  falla si encuentra frases en literales fuera de `locales/` (salvo una lista
  corta de excepciones justificadas).
- Una herramienta nueva sin sus claves en todos los diccionarios hace fallar la
  suite.

### GitHub y página web

- **README:** `README.md` pasa a inglés (es la portada de PyPI y de GitHub) y
  `README.es.md` en español, con enlaces de idioma arriba. Un idioma nuevo es otro
  `README.<código>.md`. AGENTS.md y CLAUDE.md siguen en español (son para quien
  desarrolla).
- **Página web** (repo `juanMaAV92.github.io`): el contenido de la página de
  pdf-tool sale de un diccionario por idioma; la ruta `/pdf-tool` (español) y
  `/en/pdf-tool` (inglés) se generan desde ellos, con selector de idioma y
  `hreflang`. Un idioma nuevo es otro diccionario.

### Entregas

1. Sistema de diccionarios + app + CLI + tests (con versión nueva al terminar).
2. README en inglés + `README.es.md`.
3. Página web en dos idiomas.

**Hecho cuando:** con el sistema en inglés, la app y la CLI salen en inglés sin
tocar nada; `--lang es` lo cambia; añadir un `xx.json` de prueba con todas las
claves hace que aparezca en el selector sin cambiar código; la suite sigue verde.

## Fase A — Organizar

- Organizador de páginas con miniaturas: rotar, reordenar, eliminar, extraer y
  duplicar.
- PDF a imágenes (JPG o PNG por página).

## Fase B — Preparar para enviar

- Números de página, encabezado y pie.
- Firmar o sellar: estampar la imagen de una firma en la página y posición elegidas.
- Rellenar formularios y aplanarlos (que no se puedan editar).

## Fase C — Privacidad

- Limpiar antes de compartir: metadatos, autor, adjuntos, comentarios y JavaScript.
- Tachar de verdad: buscar un texto (una cédula, un nombre) y eliminarlo del
  archivo, no solo taparlo.

## Fase D — Convertir

- PDF a Excel (tablas): PyMuPDF las detecta y `openpyxl` (~0,25 MB) escribe el
  `.xlsx`.
- PDF a Word básico: texto, párrafos e imágenes con `python-docx`, sin copiar el
  diseño exacto. Descartado `pdf2docx` (arrastra OpenCV y numpy).
- Word, Excel y PowerPoint a PDF usando Microsoft Office o LibreOffice si ya están
  instalados; si no, la herramienta lo dice claramente. No se incluye ningún motor.

## Fase E — Imprimir y reparar

- Varias páginas por hoja (2 o 4 en 1).
- Cambiar el tamaño de página (A4, Carta) y recortar márgenes.
- Pasar a escala de grises.
- Reparar un PDF dañado.

## Difusión (cuando toque)

- Probar la skill con `npx skills add` y en otro agente (p. ej. Gemini CLI).
- Demo en el README: un agente comprimiendo o uniendo PDFs.
- Listado gratuito en directorios de skills (p. ej. Agensi, skills.sh) tras revisar
  sus términos.

## Fuera de foco

- OCR, edición del contenido del PDF y AI/chat con documentos.
- Incluir motores pesados (LibreOffice, modelos de IA, OpenCV).
- Cobrar por la app, la CLI o la skill.
- Cambiar la experiencia de la app para sus usuarios no técnicos.
