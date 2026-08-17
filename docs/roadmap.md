# Roadmap

Estado actual: 6 herramientas (Comprimir, Imágenes a PDF, Unir, Proteger, Dividir,
Marca de agua) sobre un panel base compartido con lote, footer anclado, logging con
descarga y auto-update. Cada feature nueva sigue el flujo del repo: lógica pura +
panel + tests (ver AGENTS.md).

## Mantenimiento reciente

- ✅ Resultados por archivo tipados con `FileResult`; el panel ya no infiere el
  estado de una fila a partir de prefijos de texto.
- ✅ Persistencia de ajustes endurecida: JSON inválido vuelve a defaults y los
  guardados son atómicos.
- ✅ Smoke test del flujo panel real → `run_job` real → PDF real. Queda pendiente
  la validación con renderer Flet y diálogos nativos en builds de escritorio.
- ✅ Salidas PDF atómicas en todas las herramientas; el PR #30 agrupa esta
  protección con el mantenimiento de contratos y configuración.

## Próximo — alto valor

1. ~~**Vista previa (thumbnails).**~~ ✅ Hecho en #23 (inline 56px en Unir e
   Imágenes a PDF; el motor \`core/thumbnails.py\` acepta \`page_index\` — es la
   base para las futuras vistas de páginas: rotar, extraer/reordenar, Dividir
   visual).
2. ~~**Botón "Abrir archivo".**~~ ✅ Hecho en #22 (botón con salida única + icono
   por fila exitosa en lotes).
3. ~~**Sanitización de nombres para Windows.**~~ ✅ Hecho en #22 (caracteres
   `? | < > * "` + nombres reservados, validación igual en todas las plataformas).
4. ~~**No sobrescribir la salida.**~~ ✅ Hecho en las 6 herramientas. La regla
   vive solo en `core/naming.py`: `unique_path` resuelve la colisión con sufijo
   ` (n)` y `output_path` compone las salidas de nombre automático. Unir avisa
   además en vivo del nombre final, porque es la única con campo de nombre.
   Efecto lateral buscado: quedan dos sitios que deciden un directorio de
   salida, así que "carpeta de salida opcional" ya no toca seis `logic.py`.

## Después

4. ~~**Carpeta de salida opcional.**~~ ✅ Hecho: "Guardar en…" en las 6
   herramientas, con "junto al original" como default. El destino es global y
   persistente (`Settings.output_dir`), viaja por `BaseParams.output_dir` y se
   elige desde cualquier panel, encima del botón de ejecutar. El aviso de nombre
   de Unir predice sobre el destino elegido. Una carpeta guardada que ya no
   existe vuelve al default en silencio.
5. **PDF → imágenes.** El inverso de Imágenes a PDF; simétrico y barato con PyMuPDF.
6. **Rotar páginas.** Por rangos, reusando `parse_ranges` de Dividir. El caso típico:
   escaneos torcidos.

## Más adelante

7. **Extraer/reordenar páginas.** Dividir corta rangos, pero no permite "las páginas
   3, 1, 5 en ese orden".
8. **Metadatos.** Ver/limpiar título y autor; coherente con la postura de privacidad
   del logging (que ya redacta rutas).
9. **Persistir preferencias.** El destino de salida ya persiste y el archivo de
   ajustes es robusto; queda guardar tema aplicado y últimos parámetros por
   herramienta (extender `core/config.py`).

## Descartado por ahora — decisiones explícitas

- **OCR.** El salto de valor más grande (buscar texto en escaneos), pero arrastra
  Tesseract como dependencia pesada de sistema. Reevaluar si aparece una necesidad
  real.
- **Drag & drop de archivos del SO.** Flet no lo soporta en **ninguna** versión: el
  issue de 2022 ([#112](https://github.com/flet-dev/flet/issues/112)) y sus tres
  duplicados se cerraron redirigiendo a extensiones de terceros, y el PR que traía
  un DropZone nativo ([#4441](https://github.com/flet-dev/flet/pull/4441)) se cerró
  sin merge. La vía real es la extensión
  [`flet-dropzone`](https://github.com/shiena/flet-dropzone) (envuelve el paquete
  Flutter `desktop_drop`): su 0.2.0 acepta `flet>=0.27` y sería compatible con
  nuestro pin, pero lleva sin tocarse desde marzo 2025; la mantenida (0.3.x) exige
  `flet>=0.80` y por tanto la migración (deuda técnica #5). El código propio sería
  trivial —un `Dropzone` alrededor de `MultiFileToolPanel` reusando `_on_pick`, y
  las 6 herramientas lo heredan—; el riesgo está en que `flet build` tenga que
  compilar el paquete Flutter. Reevaluar cuando se pague la deuda #5, o con un
  spike de una hora si sube la prioridad antes.
- **Sufijo custom en herramientas de lote.** El nombre de salida aplica solo a
  herramientas de salida única (Unir); decidido en la spec de layout 2026-07-18.
