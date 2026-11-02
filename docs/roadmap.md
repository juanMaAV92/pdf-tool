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
- **Fase 0:** multilenguaje: añadir un idioma es añadir un diccionario, en la app, la
  CLI, el README y la página web.
- **Fase A:** Organizar páginas (miniaturas, rotar, reordenar, eliminar, extraer y
  duplicar; la app abre hasta 1000 páginas, la CLI no tiene límite) y PDF a imágenes.

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
- Listado gratuito en directorios de skills (p. ej. Agensi, skills.sh) tras revisar
  sus términos.

## Fuera de foco

- OCR, edición del contenido del PDF y AI/chat con documentos.
- Incluir motores pesados (LibreOffice, modelos de IA, OpenCV).
- Cobrar por la app, la CLI o la skill.
- Cambiar la experiencia de la app para sus usuarios no técnicos.
