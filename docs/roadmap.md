# Roadmap

Estado actual: 6 herramientas (Comprimir, Imágenes a PDF, Unir, Proteger, Dividir,
Marca de agua) sobre un panel base compartido con lote, footer anclado, logging con
descarga y auto-update. Cada feature nueva sigue el flujo del repo: lógica pura +
panel + tests (ver AGENTS.md).

## Próximo — alto valor

1. ~~**Vista previa (thumbnails).**~~ ✅ Hecho en #23 (inline 56px en Unir e
   Imágenes a PDF; el motor \`core/thumbnails.py\` acepta \`page_index\` — es la
   base para las futuras vistas de páginas: rotar, extraer/reordenar, Dividir
   visual).
2. ~~**Botón "Abrir archivo".**~~ ✅ Hecho en #22 (botón con salida única + icono
   por fila exitosa en lotes).
3. ~~**Sanitización de nombres para Windows.**~~ ✅ Hecho en #22 (caracteres
   `? | < > * "` + nombres reservados, validación igual en todas las plataformas).

## Después

4. **Carpeta de salida opcional.** "Guardar en…" con default junto al original.
   Quedó fuera de alcance en las specs de 2026-07-18; sigue siendo la limitación
   más citada en apps de este tipo.
5. **PDF → imágenes.** El inverso de Imágenes a PDF; simétrico y barato con PyMuPDF.
6. **Rotar páginas.** Por rangos, reusando `parse_ranges` de Dividir. El caso típico:
   escaneos torcidos.

## Más adelante

7. **Extraer/reordenar páginas.** Dividir corta rangos, pero no permite "las páginas
   3, 1, 5 en ese orden".
8. **Metadatos.** Ver/limpiar título y autor; coherente con la postura de privacidad
   del logging (que ya redacta rutas).
9. **Persistir preferencias.** Tema y últimos parámetros por herramienta (extender
   `core/config.py`).

## Descartado por ahora — decisiones explícitas

- **OCR.** El salto de valor más grande (buscar texto en escaneos), pero arrastra
  Tesseract como dependencia pesada de sistema. Reevaluar si aparece una necesidad
  real.
- **Drag & drop de archivos del SO.** Flet 0.28 no soporta soltar archivos desde el
  sistema en la ventana (solo drag interno). Reevaluar con versiones futuras de Flet.
- **Sufijo custom en herramientas de lote.** El nombre de salida aplica solo a
  herramientas de salida única (Unir); decidido en la spec de layout 2026-07-18.
